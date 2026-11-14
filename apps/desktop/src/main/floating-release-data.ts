import path from "node:path";
import { localTestUserDataDirectory } from "./local-test-runtime";
import { globalStableUserDataDirectory, stableUserDataDirectory } from "./user-data-bootstrap";

export function floatingReleaseDataDirectory(appData: string, version: string, floating: boolean, productionMarker: boolean, localTest: boolean, global: boolean): string {
  if (floating && !productionMarker) return path.join(localTestUserDataDirectory(appData), `floating-${version}`);
  if (localTest) return localTestUserDataDirectory(appData);
  return global ? globalStableUserDataDirectory(appData) : stableUserDataDirectory(appData);
}
