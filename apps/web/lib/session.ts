import { redirect } from "next/navigation";
import { createClient } from "./supabase/server";

export type Role = "founder" | "investor" | "mentor" | "reviewer" | "admin";
export type Status = "active" | "pending" | "suspended";
export type ViewerProfile = { role: Role; status: Status; full_name: string };

/**
 * The signed-in person and their profile, read as that person so row level
 * security applies. Sends anyone who is not signed in to the sign-in page.
 */
export async function requireViewer() {
  const supabase = await createClient();
  if (!supabase) redirect("/signin");
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/signin");
  const profile = await supabase.from("profiles").select("role, status, full_name").eq("user_id", data.user.id).maybeSingle();
  return { supabase, user: data.user, profile: (profile.data as ViewerProfile | null) ?? null };
}

/** Where a person belongs after signing in. */
export function homeFor(profile: ViewerProfile | null): string {
  if (!profile) return "/onboarding";
  if (profile.role === "investor") return profile.status === "active" ? "/investor" : "/investor/pending";
  // Only investors wait for approval, so any other account that is not active is suspended.
  if (profile.status !== "active") return "/suspended";
  if (profile.role === "reviewer" || profile.role === "admin") return "/admin";
  if (profile.role === "founder") return "/dashboard";
  // No pages exist for mentors yet, so they go to the website rather than round a loop.
  return "/";
}

/** For founder pages. Anyone else, and a suspended founder, goes to their own home. */
export async function requireFounder() {
  const v = await requireViewer();
  if (!v.profile || v.profile.role !== "founder" || v.profile.status !== "active") redirect(homeFor(v.profile));
  const venture = await v.supabase
    .from("ventures")
    .select("id, name, sector, stage, country, description, website, ask, published_at, hidden_at, hidden_reason")
    .eq("founder_id", v.user.id)
    .order("created_at", { ascending: true })
    .limit(1)
    .maybeSingle();
  if (!venture.data) redirect("/onboarding/founder");
  return { ...v, profile: v.profile, venture: venture.data };
}

/** For investor pages. A pending or declined investor goes to the waiting page. */
export async function requireInvestor() {
  const v = await requireViewer();
  if (!v.profile || v.profile.role !== "investor") redirect(homeFor(v.profile));
  if (v.profile.status !== "active") redirect("/investor/pending");
  return { ...v, profile: v.profile };
}

/** For staff pages. `admin` limits the page to admins. */
export async function requireStaff(admin = false) {
  const v = await requireViewer();
  const ok =
    v.profile?.status === "active" && (v.profile.role === "admin" || (!admin && v.profile.role === "reviewer"));
  if (!ok) redirect(homeFor(v.profile));
  return { ...v, profile: v.profile as ViewerProfile };
}
