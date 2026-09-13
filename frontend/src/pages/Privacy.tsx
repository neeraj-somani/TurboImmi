import LegalPage from "./LegalPage";

export default function Privacy() {
  return (
    <LegalPage title="Privacy Policy">
      <p>
        This draft describes how the P0 helper intends to handle data. Counsel must review it before
        any public launch. Do not treat this page as a finished privacy notice.
      </p>
      <p>
        Account sign-in uses Amazon Cognito. Profile and case fields you save are stored so you can
        continue later. Uploaded passport or offer-letter files are kept in a private bucket, expire
        after 14 days, and can be deleted after you confirm or via “Delete my uploads.”
      </p>
      <p>
        We do not put secrets or passport images in the public website bundle. AI extract text is
        not written to application logs. The validation score is completeness only — not an
        approval prediction.
      </p>
      <p>
        TurboImmi is not affiliated with USCIS or DHS. Official policy always lives on USCIS.gov.
      </p>
    </LegalPage>
  );
}
