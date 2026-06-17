import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { OwnerProvider } from "./owner";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Cockpit from "./pages/Cockpit";
import Carteira from "./pages/Carteira";
import Inativos from "./pages/Inativos";
import Oportunidades from "./pages/Oportunidades";
import Admin from "./pages/Admin";

export default function App() {
  const { user, loading } = useAuth();

  if (loading)
    return (
      <div className="grid h-full place-items-center text-slate-400">Carregando…</div>
    );

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <OwnerProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Cockpit />} />
          <Route path="/carteira" element={<Carteira />} />
          <Route path="/inativos" element={<Inativos />} />
          <Route path="/oportunidades" element={<Oportunidades />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </OwnerProvider>
  );
}
