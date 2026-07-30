// Data schema for the DashboardWalkthrough onboarding tutorial (sign-in -> profile creation ->
// dashboard tour). Real UI screenshots off the Creative Display demo org ("Horizon Youth
// Collective"), captured 2026-07-03 against the redesigned IA (Home / Snapshot / Ecosystem /
// Opportunities / Pipeline / Readiness / Organization — the same 7 steps as the app's own
// in-product guided tour, see _app_shell_sidebar.html).

export type WalkSection = {
  id: string;
  label: string; // short on-screen section label (matches the app's left-nav labels)
  shot: string; // screenshot filename in public/screenshots/
  tone: "teal" | "gold";
};

export const WALK_SECTIONS: WalkSection[] = [
  { id: "signin", label: "Sign In", shot: "shot-signin.png", tone: "teal" },
  { id: "intake", label: "Creating Your Profile", shot: "shot-intake.png", tone: "gold" },
  { id: "tour1", label: "Home", shot: "shot-tour-step1.png", tone: "gold" },
  { id: "dashboard", label: "Home", shot: "shot-dashboard3.png", tone: "gold" },
  { id: "tour2", label: "Snapshot", shot: "shot-tour-step2.png", tone: "gold" },
  { id: "snapshot", label: "Snapshot", shot: "shot-snapshot3.png", tone: "gold" },
  { id: "ecosystem", label: "Ecosystem", shot: "shot-ecosystem3.png", tone: "teal" },
  { id: "opportunities", label: "Opportunities", shot: "shot-opportunities3.png", tone: "teal" },
  { id: "pipeline", label: "Pipeline", shot: "shot-pipeline3.png", tone: "gold" },
  { id: "readiness", label: "Readiness", shot: "shot-readiness3.png", tone: "gold" },
  { id: "organization", label: "Organization", shot: "shot-organization3.png", tone: "teal" },
];

export const bySectionId = (id: string) => WALK_SECTIONS.find((s) => s.id === id)!;
