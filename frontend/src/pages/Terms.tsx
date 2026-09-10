import LegalPage from "./LegalPage";

export default function Terms() {
  return (
    <LegalPage title="Terms of Service">
      <p>
        TurboImmi is an educational helper for U.S. immigration paperwork, starting with H-1B. It is
        not a law firm and does not provide legal advice. You must have a licensed immigration
        attorney review forms, evidence, and strategy before filing with USCIS or any agency.
      </p>
      <p>
        Validation scores measure completeness and internal consistency only. They are not approval
        odds and are not a government determination. The attorney directory is referral and
        discovery only. TurboImmi does not assign counsel.
      </p>
      <p>
        TurboImmi is not affiliated with, endorsed by, or sponsored by USCIS or DHS. Always verify
        policy on the official USCIS.gov page.
      </p>
      <p>
        After you choose Applicant or Attorney, that role is locked for the account. Do not upload
        documents you are not allowed to share. Uploaded files are treated as personal data, expire
        after 14 days, and can be deleted by you.
      </p>
    </LegalPage>
  );
}
