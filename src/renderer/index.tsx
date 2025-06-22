/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import App from "./App";
import "./global.css";
import "./index.css";
// default styling
import { createRoot } from "react-dom/client";
import "reactflow/dist/style.css";

// or if you just want basic styles
import "reactflow/dist/base.css";

import { ErrorBoundary } from "react-error-boundary";
import { ErrorPage } from "@/renderer/ErrorPage";
import { HashRouter } from "react-router-dom";
import { AuthContextProvider } from "./context/auth.context";
import { ThemeProvider } from "./providers/theme-provider";
import { TestSequencerWSProvider } from "./context/testSequencerWS.context";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const root = createRoot(document.getElementById("root") as HTMLElement);
const queryClient = new QueryClient();

function fallbackRender({ error, resetErrorBoundary }) {
  return <ErrorPage error={error} resetErrorBoundary={resetErrorBoundary} />;
}

root.render(
  /** Using HashRouter as BrowserRouter doesn't work after build */
  <HashRouter>
    <ErrorBoundary fallbackRender={fallbackRender}>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <QueryClientProvider client={queryClient}>
          <AuthContextProvider>
            <TestSequencerWSProvider>
              <App />
            </TestSequencerWSProvider>
          </AuthContextProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </HashRouter>,
);
