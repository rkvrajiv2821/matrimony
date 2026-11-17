import type { ReactNode } from "react";

// The [locale] layout renders <html>/<body>; this root exists only because Next requires one.
export default function RootLayout({ children }: { children: ReactNode }) {
  return children;
}
