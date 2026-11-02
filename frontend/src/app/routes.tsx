export type AlphaRoute = {
  label: string;
  path: string;
  story: string;
};

export const alphaRoutes: AlphaRoute[] = [
  { path: "/", label: "Gallery upload and target", story: "US-01/US-03" },
  { path: "/brief", label: "Creative brief", story: "US-02" },
  { path: "/comparisons", label: "Adaptive comparisons", story: "US-05" },
  { path: "/review", label: "Gallery review and export", story: "US-06–US-09" },
  { path: "/evaluation", label: "Satisfaction feedback", story: "US-10" },
];

