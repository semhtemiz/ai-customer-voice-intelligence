"use client";

import * as React from "react";
import { IconMoon, IconSun } from "@tabler/icons-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

const subscribe = () => () => {};
const clientSnapshot = () => true;
const serverSnapshot = () => false;

export function ThemeToggle() {
  const { setTheme, resolvedTheme } = useTheme();
  const mounted = React.useSyncExternalStore(subscribe, clientSnapshot, serverSnapshot);

  return (
    <Button
      variant="ghost"
      size="icon"
      className="rounded-full"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label="Temayı değiştir"
    >
      {mounted && resolvedTheme === "dark" ? (
        <IconSun className="size-5" />
      ) : (
        <IconMoon className="size-5" />
      )}
    </Button>
  );
}
