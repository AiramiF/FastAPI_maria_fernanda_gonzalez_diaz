import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Layout } from "./components/Layout";
import { BookDetailPage } from "./pages/BookDetailPage";
import { CatalogPage } from "./pages/CatalogPage";
import { MemberLoansPage, ProfilePage } from "./pages/AccountPages";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { MemberLoansHistoryPage, StaffPanelPage } from "./pages/StaffPanelPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CatalogPage />} />
        <Route path="libros/:id" element={<BookDetailPage />} />
        <Route path="registro" element={<RegisterPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="perfil" element={<ProfilePage />} />
        </Route>
        <Route element={<ProtectedRoute roles={["socio"]} />}>
          <Route path="mis-prestamos" element={<MemberLoansPage />} />
          <Route path="mis-multas" element={<MemberLoansPage finesOnly />} />
        </Route>
        <Route element={<ProtectedRoute roles={["admin"]} />}>
          <Route path="panel/usuarios" element={<StaffPanelPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={["admin", "bibliotecario"]} />}>
          <Route path="panel" element={<StaffPanelPage />} />
          <Route path="panel/libros" element={<StaffPanelPage />} />
          <Route path="panel/autores" element={<StaffPanelPage />} />
          <Route path="panel/categorias" element={<StaffPanelPage />} />
          <Route path="panel/socios" element={<StaffPanelPage />} />
          <Route path="panel/prestamos" element={<StaffPanelPage />} />
          <Route path="panel/reportes" element={<StaffPanelPage />} />
          <Route path="panel/socios/:id/prestamos" element={<MemberLoansHistoryPage />} />
        </Route>
        <Route path="404" element={<NotFoundPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}
