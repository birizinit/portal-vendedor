import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "./auth";

interface OwnerCtx {
  ownerId: number | null;
  setOwnerId: (id: number | null) => void;
  isAdmin: boolean;
}

const Ctx = createContext<OwnerCtx>(null!);
const KEY = "portal_owner_id";

export function OwnerProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [ownerId, setOwnerIdState] = useState<number | null>(() => {
    const saved = localStorage.getItem(KEY);
    return saved ? Number(saved) : null;
  });

  // vendedor: força o próprio owner_id
  useEffect(() => {
    if (user && !isAdmin) setOwnerIdState(user.owner_id ?? null);
  }, [user, isAdmin]);

  const setOwnerId = (id: number | null) => {
    setOwnerIdState(id);
    if (id) localStorage.setItem(KEY, String(id));
    else localStorage.removeItem(KEY);
  };

  return (
    <Ctx.Provider value={{ ownerId, setOwnerId, isAdmin }}>{children}</Ctx.Provider>
  );
}

export const useOwner = () => useContext(Ctx);
