import { createContext, useContext, type Dispatch, type SetStateAction } from "react";
import type { WebAppState } from "./domain";

interface PrototypeContextValue {
  authenticated: boolean;
  setAuthenticated(value: boolean): void;
  state: WebAppState;
  setState: Dispatch<SetStateAction<WebAppState>>;
  logout(): Promise<void>;
}

export const PrototypeContext = createContext<PrototypeContextValue | null>(null);

export const usePrototype = () => {
  const value = useContext(PrototypeContext);
  if (!value) throw new Error("Prototype context is unavailable");
  return value;
};
