import { alphaRoutes } from "./routes";

export function App() {
  return (
    <main>
      <h1>SelectIQ Alpha</h1>
      <p>The Alpha workflow is scaffolded and ready for test-driven implementation.</p>
      <ol>
        {alphaRoutes.map((route) => (
          <li key={route.path}>
            {route.story}: {route.label}
          </li>
        ))}
      </ol>
    </main>
  );
}

