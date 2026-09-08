// Local design review only. Not included in production Rollup entry points.
import { createRoot } from "react-dom/client";
import { useEffect } from "react";
import { App } from "../App";
import type { WebAppState } from "../domain";
import { syntheticState } from "../../../web/src/test-state";

window.history.replaceState({}, "", "/#why-offersteady");
function DesignPreview() {
  useEffect(() => { document.getElementById("why-offersteady")?.scrollIntoView({ block: "start" }); }, []);
  return <App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />;
}
createRoot(document.getElementById("root")!).render(<DesignPreview />);
