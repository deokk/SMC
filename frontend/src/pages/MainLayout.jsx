import { useState } from "react";
import { Outlet } from "react-router-dom";

export default function MainLayout() {
  // State to be preserved across pages
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [routes, setRoutes] = useState(null);
  const [isRoutesOpen, setIsRoutesOpen] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState(null);

  const context = {
    from,
    setFrom,
    to,
    setTo,
    routes,
    setRoutes,
    isRoutesOpen,
    setIsRoutesOpen,
    selectedRoute,
    setSelectedRoute,
  };

  return <Outlet context={context} />;
}
