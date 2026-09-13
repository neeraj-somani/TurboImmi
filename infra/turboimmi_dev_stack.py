"""P0 TurboImmi stack. Day 0 budget + Day 2 hello path + Day 3 role APIs (same stack)."""

from __future__ import annotations

import os
from pathlib import Path

from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Duration,
    Environment,
    RemovalPolicy,
    Stack,
    Tags,
)
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_authorizers as apigwv2_auth
from aws_cdk import aws_apigatewayv2_integrations as apigwv2_int
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

from lambda_bundling import LambdaLocalBundling

BUDGET_NAME = "turboimmi-dev-monthly"
SYNTH_PLACEHOLDER_EMAIL = "placeholder@example.com"
REPO = Path(__file__).resolve().parent.parent
LOCALHOST = "http://localhost:5173"


def _budget_alert_email() -> str:
    email = (os.environ.get("BUDGET_ALERT_EMAIL") or "").strip()
    if email:
        return email
    return SYNTH_PLACEHOLDER_EMAIL


def _cognito_prefix() -> str:
    prefix = (os.environ.get("COGNITO_DOMAIN_PREFIX") or "turboimmi-dev").strip()
    return prefix or "turboimmi-dev"


def _github_repo() -> str:
    return (
        os.environ.get("GITHUB_REPOSITORY")
        or os.environ.get("GITHUB_REPO")
        or "example/turboimmi"
    ).strip()


def _github_oidc_subs(repo: str) -> list[str]:
    """Trust main from this repo under both GitHub OIDC subject formats.

    Repos created after 2026-07-15 send immutable owner/repo IDs:
    repo:owner@id/name@id:ref:refs/heads/main
    Older repos still send repo:owner/name:ref:refs/heads/main
    """
    repo = repo.strip()
    owner, sep, name = repo.partition("/")
    subs = [f"repo:{repo}:ref:refs/heads/main"]
    if sep and owner and name:
        subs.append(f"repo:{owner}@*/{name}@*:ref:refs/heads/main")
    return subs


class TurboImmiDevStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env: Environment | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, env=env, **kwargs)

        Tags.of(self).add("Project", "TurboImmi")
        Tags.of(self).add("Env", "dev")

        self._budget()
        pool, hosted_domain = self._cognito()
        web_bucket, distribution, cf_https = self._spa()
        client = self._finish_cognito(pool, cf_https)
        docs_bucket = self._docs_bucket(cf_https)
        tables = self._tables()
        api = self._api(pool, client, distribution, tables, docs_bucket, cf_https)
        self._spa_deploy(web_bucket, distribution, api, pool, client)
        deploy_role = self._github_oidc(web_bucket)

        CfnOutput(self, "CloudFrontUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "ApiUrl", value=api.api_endpoint)
        CfnOutput(self, "UserPoolId", value=pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=client.user_pool_client_id)
        CfnOutput(self, "CognitoDomain", value=self._hosted_ui_url())
        CfnOutput(self, "WebBucketName", value=web_bucket.bucket_name)
        CfnOutput(self, "DocsBucketName", value=docs_bucket.bucket_name)
        CfnOutput(self, "DistributionId", value=distribution.distribution_id)
        CfnOutput(self, "GitHubDeployRoleArn", value=deploy_role.role_arn)

    def _hosted_ui_url(self) -> str:
        return f"https://{_cognito_prefix()}.auth.{self.region}.amazoncognito.com"

    def _budget(self) -> None:
        email = _budget_alert_email()
        subscribers = [
            budgets.CfnBudget.SubscriberProperty(
                subscription_type="EMAIL",
                address=email,
            )
        ]

        def notify(
            notification_type: str, threshold: float
        ) -> budgets.CfnBudget.NotificationWithSubscribersProperty:
            return budgets.CfnBudget.NotificationWithSubscribersProperty(
                notification=budgets.CfnBudget.NotificationProperty(
                    notification_type=notification_type,
                    comparison_operator="GREATER_THAN",
                    threshold=threshold,
                    threshold_type="PERCENTAGE",
                ),
                subscribers=subscribers,
            )

        budget = budgets.CfnBudget(
            self,
            "MonthlyCostBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=BUDGET_NAME,
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(amount=10, unit="USD"),
            ),
            notifications_with_subscribers=[
                notify("ACTUAL", 80),
                notify("ACTUAL", 100),
                notify("FORECASTED", 100),
            ],
        )
        budget.apply_removal_policy(RemovalPolicy.RETAIN)

    def _cognito(self) -> tuple:
        pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name="turboimmi-dev",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            password_policy=cognito.PasswordPolicy(min_length=8),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
        )
        cognito.CfnUserPoolGroup(
            self, "ApplicantGroup", user_pool_id=pool.user_pool_id, group_name="Applicant"
        )
        cognito.CfnUserPoolGroup(
            self, "AttorneyGroup", user_pool_id=pool.user_pool_id, group_name="Attorney"
        )
        cognito.CfnUserPoolGroup(
            self, "AdminGroup", user_pool_id=pool.user_pool_id, group_name="Admin"
        )
        hosted_domain = pool.add_domain(
            "HostedUi",
            cognito_domain=cognito.CognitoDomainOptions(domain_prefix=_cognito_prefix()),
        )
        return pool, hosted_domain

    def _spa(self) -> tuple[s3.Bucket, cloudfront.Distribution, str]:
        web_bucket = s3.Bucket(
            self,
            "WebBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        spa_origin = origins.S3BucketOrigin.with_origin_access_control(web_bucket)
        distribution = cloudfront.Distribution(
            self,
            "SpaCdn",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=spa_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            additional_behaviors={
                "/config.json": cloudfront.BehaviorOptions(
                    origin=spa_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                )
            },
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(1),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(1),
                ),
            ],
        )
        cf_https = f"https://{distribution.distribution_domain_name}"
        return web_bucket, distribution, cf_https

    def _finish_cognito(self, pool: cognito.UserPool, cf_https: str) -> cognito.UserPoolClient:
        callbacks = [LOCALHOST, cf_https]
        return pool.add_client(
            "SpaClient",
            user_pool_client_name="turboimmi-dev-spa",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(user_srp=True),
            prevent_user_existence_errors=True,
            supported_identity_providers=[cognito.UserPoolClientIdentityProvider.COGNITO],
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=callbacks,
                logout_urls=callbacks,
            ),
        )

    def _docs_bucket(self, cf_https: str) -> s3.Bucket:
        return s3.Bucket(
            self,
            "DocsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(enabled=True, expiration=Duration.days(14)),
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.HEAD,
                        s3.HttpMethods.DELETE,
                    ],
                    allowed_origins=[LOCALHOST, cf_https],
                    allowed_headers=["*"],
                    max_age=3600,
                )
            ],
        )

    def _tables(self) -> dict[str, dynamodb.Table]:
        def shell(construct_id: str, table_name: str, ttl: str | None = None) -> dynamodb.Table:
            kwargs: dict = {
                "table_name": table_name,
                "partition_key": dynamodb.Attribute(
                    name="pk", type=dynamodb.AttributeType.STRING
                ),
                "sort_key": dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
                "billing_mode": dynamodb.BillingMode.PAY_PER_REQUEST,
                "encryption": dynamodb.TableEncryption.AWS_MANAGED,
                "removal_policy": RemovalPolicy.RETAIN,
                "point_in_time_recovery_specification": dynamodb.PointInTimeRecoverySpecification(
                    point_in_time_recovery_enabled=True
                ),
            }
            if ttl:
                kwargs["time_to_live_attribute"] = ttl
            return dynamodb.Table(self, construct_id, **kwargs)

        tables = {
            "users": shell("Users", "turboimmi-dev-users"),
            "cases": shell("Cases", "turboimmi-dev-cases"),
            "prefill": shell("PrefillJobs", "turboimmi-dev-prefill-jobs", ttl="expiresAt"),
            "attorneys": shell("Attorneys", "turboimmi-dev-attorneys"),
            "consults": shell("Consults", "turboimmi-dev-consults"),
            "alerts": shell("Alerts", "turboimmi-dev-alerts"),
            "policy": shell("PolicyChunks", "turboimmi-dev-policy-chunks"),
            "audit": shell("AiAudit", "turboimmi-dev-ai-audit", ttl="expiresAt"),
        }
        tables["attorneys"].add_global_secondary_index(
            index_name="gsi1",
            partition_key=dynamodb.Attribute(
                name="gsi1pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="gsi1sk", type=dynamodb.AttributeType.STRING),
        )
        tables["consults"].add_global_secondary_index(
            index_name="gsi1",
            partition_key=dynamodb.Attribute(
                name="gsi1pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="gsi1sk", type=dynamodb.AttributeType.STRING),
        )
        return tables

    def _api(
        self,
        pool: cognito.UserPool,
        client: cognito.UserPoolClient,
        distribution: cloudfront.Distribution,
        tables: dict[str, dynamodb.Table],
        docs_bucket: s3.Bucket,
        cf_https: str,
    ) -> apigwv2.HttpApi:
        fn = lambda_.Function(
            self,
            "ApiFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            handler="app.main.handler",
            memory_size=512,
            timeout=Duration.seconds(45),
            environment={
                "CORS_ORIGINS": f"{LOCALHOST},{cf_https}",
                "USER_POOL_ID": pool.user_pool_id,
                "USERS_TABLE": tables["users"].table_name,
                "CASES_TABLE": tables["cases"].table_name,
                "PREFILL_TABLE": tables["prefill"].table_name,
                "ATTORNEYS_TABLE": tables["attorneys"].table_name,
                "CONSULTS_TABLE": tables["consults"].table_name,
                "ALERTS_TABLE": tables["alerts"].table_name,
                "POLICY_TABLE": tables["policy"].table_name,
                "AUDIT_TABLE": tables["audit"].table_name,
                "DOCS_BUCKET": docs_bucket.bucket_name,
                "BEDROCK_VISION_MODEL_ID": os.environ.get("BEDROCK_VISION_MODEL_ID", ""),
                "BEDROCK_CHAT_MODEL_ID": os.environ.get("BEDROCK_CHAT_MODEL_ID", ""),
                "BEDROCK_EMBED_MODEL_ID": os.environ.get("BEDROCK_EMBED_MODEL_ID", ""),
                "ADMIN_ALLOWLIST_EMAIL": os.environ.get("ADMIN_ALLOWLIST_EMAIL", ""),
            },
            code=lambda_.Code.from_asset(
                str(REPO),
                exclude=[
                    ".git",
                    ".github",
                    ".cursor",
                    "frontend",
                    "infra/cdk.out",
                    "infra/.venv",
                    "backend/.venv",
                    "backend/tests",
                    "docs",
                    "**/__pycache__",
                    "node_modules",
                ],
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    local=LambdaLocalBundling(),
                    command=[
                        "bash",
                        "-c",
                        "pip install -r backend/requirements-lambda.txt -t /asset-output && "
                        "cp -R backend/app /asset-output/app && "
                        "mkdir -p /asset-output/shared/policy && "
                        "cp shared/disclaimer.json /asset-output/shared/disclaimer.json && "
                        "cp -R shared/policy /asset-output/shared/policy",
                    ],
                ),
            ),
        )
        for table in tables.values():
            table.grant_read_write_data(fn)
        docs_bucket.grant_read_write(fn)
        fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="CognitoRoleAssign",
                actions=[
                    "cognito-idp:AdminAddUserToGroup",
                    "cognito-idp:AdminListGroupsForUser",
                ],
                resources=[pool.user_pool_arn],
            )
        )
        fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockExtract",
                actions=["bedrock:InvokeModel"],
                resources=[
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*::foundation-model/*",
                ],
            )
        )

        jwt_auth = apigwv2_auth.HttpJwtAuthorizer(
            "CognitoJwt",
            jwt_issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{pool.user_pool_id}",
            jwt_audience=[client.user_pool_client_id],
        )
        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            api_name="turboimmi-dev",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=[LOCALHOST, cf_https],
                allow_methods=[apigwv2.CorsHttpMethod.ANY],
                allow_headers=["Authorization", "Content-Type"],
                max_age=Duration.hours(1),
            ),
        )
        integration = apigwv2_int.HttpLambdaIntegration("ApiInt", fn)
        http_api.add_routes(
            path="/health",
            methods=[apigwv2.HttpMethod.GET],
            integration=integration,
        )
        http_api.add_routes(
            path="/disclaimer",
            methods=[apigwv2.HttpMethod.GET],
            integration=integration,
        )
        http_api.add_routes(
            path="/health/auth",
            methods=[apigwv2.HttpMethod.GET],
            integration=integration,
            authorizer=jwt_auth,
        )
        http_api.add_routes(
            path="/{proxy+}",
            methods=[
                apigwv2.HttpMethod.GET,
                apigwv2.HttpMethod.POST,
                apigwv2.HttpMethod.PUT,
                apigwv2.HttpMethod.PATCH,
                apigwv2.HttpMethod.DELETE,
            ],
            integration=integration,
            authorizer=jwt_auth,
        )
        default_stage = http_api.default_stage
        if default_stage is not None:
            cfn_stage = default_stage.node.default_child
            if cfn_stage is not None:
                cfn_stage.default_route_settings = apigwv2.CfnStage.RouteSettingsProperty(
                    throttling_burst_limit=100,
                    throttling_rate_limit=50,
                )
        return http_api

    def _spa_deploy(
        self,
        web_bucket: s3.Bucket,
        distribution: cloudfront.Distribution,
        api: apigwv2.HttpApi,
        pool: cognito.UserPool,
        client: cognito.UserPoolClient,
    ) -> None:
        dist_dir = REPO / "frontend" / "dist"
        if not dist_dir.is_dir():
            raise RuntimeError("frontend/dist missing — run npm run build in frontend/")
        cf_https = f"https://{distribution.distribution_domain_name}"
        s3deploy.BucketDeployment(
            self,
            "SpaDeploy",
            destination_bucket=web_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
            sources=[
                s3deploy.Source.asset(str(dist_dir)),
                s3deploy.Source.json_data(
                    "config.json",
                    {
                        "apiBaseUrl": api.api_endpoint,
                        "userPoolId": pool.user_pool_id,
                        "userPoolClientId": client.user_pool_client_id,
                        "cognitoDomain": self._hosted_ui_url(),
                        "region": self.region,
                        "redirectUri": cf_https,
                    },
                ),
            ],
        )

    def _github_oidc(self, web_bucket: s3.Bucket) -> iam.Role:
        repo = _github_repo()
        provider = iam.OpenIdConnectProvider(
            self,
            "GitHubOidc",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )
        role = iam.Role(
            self,
            "GitHubDeployRole",
            role_name="turboimmi-dev-github-deploy",
            description="GitHub Actions OIDC deploy from main. No long-lived keys.",
            assumed_by=iam.OpenIdConnectPrincipal(
                provider,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": _github_oidc_subs(repo),
                    },
                },
            ),
        )
        account = self.account
        region = self.region
        qualifier = "hnb659fds"
        role.add_to_policy(
            iam.PolicyStatement(
                sid="AssumeCdkBootstrap",
                actions=["sts:AssumeRole"],
                resources=[
                    f"arn:aws:iam::{account}:role/cdk-{qualifier}-deploy-role-{account}-{region}",
                    f"arn:aws:iam::{account}:role/cdk-{qualifier}-file-publishing-role-{account}-{region}",
                    f"arn:aws:iam::{account}:role/cdk-{qualifier}-image-publishing-role-{account}-{region}",
                    f"arn:aws:iam::{account}:role/cdk-{qualifier}-lookup-role-{account}-{region}",
                ],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                sid="ReadStackOutputs",
                actions=["cloudformation:DescribeStacks", "cloudformation:ListStacks"],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                sid="SyncSpa",
                actions=[
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                ],
                resources=[web_bucket.bucket_arn, f"{web_bucket.bucket_arn}/*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                sid="InvalidateSpa",
                actions=["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"],
                resources=["*"],
            )
        )
        return role
