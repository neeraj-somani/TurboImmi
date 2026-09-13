import { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import disclaimer from "../../shared/disclaimer.json";
import { apiJson, homePath, type Me } from "./api";
import {
  completeHostedUiLogin,
  getIdToken,
  loadSpaConfig,
  type SpaConfig,
} from "./auth";
import { isDisclaimerAccepted, isLegalPath } from "./disclaimerAck";
import AdminHome from "./pages/AdminHome";
import ApplicantHome from "./pages/ApplicantHome";
import AttorneyHome from "./pages/AttorneyHome";
import DisclaimerGate from "./pages/DisclaimerGate";
import Landing from "./pages/Landing";
import Privacy from "./pages/Privacy";
import RoleChooser from "./pages/RoleChooser";
import Terms from "./pages/Terms";
import { SpaContext } from "./spa";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [config, setConfig] = useState<SpaConfig | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [ready, setReady] = useState(false);
  const [disclaimerOk, setDisclaimerOk] = useState(() => isDisclaimerAccepted(disclaimer.version));

  const reloadMe = useCallback(async (): Promise<Me | null> => {
    if (!config || !getIdToken()) {
      setMe(null);
      return null;
    }
    try {
      const next = await apiJson<Me>(config, "/me");
      setMe(next);
      return next;
    } catch {
      setMe(null);
      return null;
    }
  }, [config]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const loaded = await loadSpaConfig();
      if (cancelled) {
        return;
      }
      setConfig(loaded);
      if (loaded.userPoolClientId) {
        const exchanged = await completeHostedUiLogin(loaded);
        if (exchanged || getIdToken()) {
          setSignedIn(true);
        }
        if (exchanged) {
          navigate(window.location.pathname || "/", { replace: true });
        }
      }
      setReady(true);
    })().catch(() => {
      if (!cancelled) {
        setReady(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  useEffect(() => {
    if (!config || !signedIn) {
      return;
    }
    void reloadMe();
  }, [config, signedIn, reloadMe]);

  const value = useMemo(
    () =>
      config
        ? {
            config,
            me,
            signedIn,
            reloadMe,
          }
        : null,
    [config, me, reloadMe, signedIn],
  );

  if (!ready || !config || !value) {
    return (
      <main className="min-h-screen bg-slate-50 px-6 py-16 text-slate-600">Loading TurboImmi…</main>
    );
  }

  if (!disclaimerOk && !isLegalPath(location.pathname)) {
    return (
      <SpaContext.Provider value={value}>
        <DisclaimerGate onAccepted={() => setDisclaimerOk(true)} />
      </SpaContext.Provider>
    );
  }

  return (
    <SpaContext.Provider value={value}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/choose-role" element={<RoleChooser />} />
        <Route path="/app" element={<ApplicantHome />} />
        <Route path="/attorney" element={<AttorneyHome />} />
        <Route path="/admin" element={<AdminHome />} />
        <Route
          path="*"
          element={<Navigate to={signedIn && me ? homePath(me) : "/"} replace />}
        />
      </Routes>
    </SpaContext.Provider>
  );
}
