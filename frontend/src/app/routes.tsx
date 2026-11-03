export type AlphaRoute = {
  label: string;
  path: string;
  story: string;
};

export const alphaRoutes: AlphaRoute[] = [
  { path: "/", label: "Gallery upload", story: "A-01" },
  { path: "/brief", label: "Prompt and target", story: "A-02" },
  { path: "/comparisons", label: "Pairwise feedback", story: "A-05/A-06" },
  { path: "/review", label: "Gallery review and export", story: "A-07/A-08" },
  { path: "/evaluation", label: "Satisfaction feedback", story: "A-09/A-10" },
];

