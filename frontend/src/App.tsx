import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./components/layout/MainLayout";
import Dashboard from "./features/dashboard/Dashboard";
import ArchitectureView from "./features/architecture/ArchitectureView";
import AIChatView from "./features/chat/AIChatView";
import SettingsView from "./features/settings/SettingsView";
import { AnalysisProvider } from "./context/AnalysisContext";

function App() {
  return (
    <BrowserRouter>
      <AnalysisProvider>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="architecture" element={<ArchitectureView />} />
            <Route path="chat" element={<AIChatView />} />
            <Route path="settings" element={<SettingsView />} />
          </Route>
        </Routes>
      </AnalysisProvider>
    </BrowserRouter>
  );
}

export default App;
