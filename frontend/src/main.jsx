import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
<<<<<<< HEAD
=======
import { AuthProvider } from "./context/AuthContext.jsx";
>>>>>>> backend
import "../styles/globals.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
<<<<<<< HEAD
    <App />
=======
    <AuthProvider>
      <App />
    </AuthProvider>
>>>>>>> backend
  </StrictMode>
);
