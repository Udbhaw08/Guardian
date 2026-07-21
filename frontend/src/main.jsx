import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import Feed from "@/pages/Feed";
import Analytics from "@/pages/Analytics";
import Detectors from "@/pages/Detectors";
import Policy from "@/pages/Policy";
import "@fontsource/fira-sans/300.css";
import "@fontsource/fira-sans/400.css";
import "@fontsource/fira-sans/500.css";
import "@fontsource/fira-sans/600.css";
import "@fontsource/fira-sans/700.css";
import "@fontsource/fira-code/400.css";
import "@fontsource/fira-code/500.css";
import "@fontsource/fira-code/600.css";
import "@fontsource/fira-code/700.css";
import "./index.css";

// Remove the overview/vision mockup completely.
// Root page is the live Scan Activity Feed.
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Feed /> },
      { path: "feed", element: <Navigate to="/" replace /> },
      { path: "analytics", element: <Analytics /> },
      { path: "detectors", element: <Detectors /> },
      { path: "policy", element: <Policy /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
