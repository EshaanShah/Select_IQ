export type AlphaRoute = {
  label: string;
  path: string;
  story: string;
};

export const alphaRoutes: AlphaRoute[] = [
  { path: "/", label: "Gallery", story: "A-01/A-11" },
  { path: "/direction", label: "Creative direction", story: "A-02/A-11" },
  { path: "/analysis", label: "AI analysis", story: "A-03/A-04/A-11" },
  { path: "/compare", label: "Pairwise comparison", story: "A-05/A-06/A-11" },
  { path: "/review", label: "Gallery review", story: "A-07/A-08/A-11" },
  { path: "/export", label: "Export", story: "A-08/A-11" },
];

