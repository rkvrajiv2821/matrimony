"use client";

import { useRouter } from "@/i18n/navigation";
import { postJson } from "@/lib/errors";
import { useState } from "react";

export function LogoutButton({ label, allDevices = false }: { label: string; allDevices?: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      disabled={busy}
      data-testid={allDevices ? "logout-all" : "logout"}
      onClick={async () => {
        setBusy(true);
        await postJson("/api/auth/logout", { all_devices: allDevices });
        router.replace("/");
        router.refresh();
      }}
      className={
        allDevices
          ? "inline-flex min-h-11 items-center rounded-full border border-danger px-4 text-sm font-semibold text-danger hover:bg-danger-soft"
          : "inline-flex min-h-11 items-center rounded-full px-4 text-sm font-medium text-muted hover:bg-primary-soft hover:text-primary"
      }
    >
      {label}
    </button>
  );
}
