/**
 * tsx compiles .tsx files with the classic JSX runtime when it runs from the
 * repo root and finds no tsconfig there (the root `npm test` script does
 * exactly that). Classic JSX emits free `React.createElement` and
 * `React.Fragment` references, which raise "React is not defined" for
 * components that rely on the app's automatic runtime.
 *
 * Providing the React namespace on the global scope makes those emitted
 * references resolve, so every component module renders identically under
 * either JSX runtime. Test assertions are unchanged by this shim.
 */
import * as React from "react";

(globalThis as { React?: unknown }).React = React;
