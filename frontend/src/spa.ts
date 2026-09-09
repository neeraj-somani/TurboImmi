import { createContext, useContext } from "react";
import type { Me } from "./api";
import type { SpaConfig } from "./auth";

export type SpaState = {
  config: SpaConfig;
  me: Me | null;
  signedIn: boolean;
  reloadMe: () => Promise<Me | null>;
};

export const SpaContext = createContext<SpaState | null>(null);

export function useSpa(): SpaState {
  const value = useContext(SpaContext);
  if (!value) {
    throw new Error("SpaContext missing");
  }
  return value;
}
