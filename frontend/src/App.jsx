import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./pages/MainLayout";
import MainPage from "./pages/MainPage/MainPage";
import RouteDetailPage from "./pages/RouteDetailPage/RouteDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<MainPage />} />
          <Route path="route-detail" element={<RouteDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}