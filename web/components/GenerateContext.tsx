"use client";

import { createContext, useContext, useRef } from "react";

type Start = (query: string) => void;
const Ctx = createContext<{ generate: Start; startRef: React.RefObject<Start | null> } | null>(null);

/** Lets the catalog start a generation in the Generator elsewhere on the page. */
export function GenerateProvider({ children }: { children: React.ReactNode }) {
  const startRef = useRef<Start | null>(null);
  const generate = (query: string) => {
    if (startRef.current === null) throw new Error("no Generator is mounted inside <GenerateProvider>");
    startRef.current(query);
    document.getElementById("generate")?.scrollIntoView({ behavior: "smooth" });
  };
  return <Ctx.Provider value={{ generate, startRef }}>{children}</Ctx.Provider>;
}

export function useGenerate() {
  const ctx = useContext(Ctx);
  if (ctx === null) throw new Error("useGenerate must be used inside <GenerateProvider>");
  return ctx;
}
