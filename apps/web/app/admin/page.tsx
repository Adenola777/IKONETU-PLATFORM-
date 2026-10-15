import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  await requireStaff();
  redirect("/admin/evidence");
}
