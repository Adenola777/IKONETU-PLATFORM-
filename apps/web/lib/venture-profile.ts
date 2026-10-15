import type { SupabaseClient } from "@supabase/supabase-js";
import { isShownStatus, type ShownStatus } from "./product";

export type ProfileEvidence = {
  id: string; category: string; label: string; summary: string | null; status: ShownStatus;
  publicNote: string | null; reviewedAt: string | null; createdAt: string;
};

export type VentureProfile = {
  venture: { id: string; name: string; sector: string; stage: string; country: string; description: string | null; website: string | null; published_at: string | null };
  founder: { full_name: string; city: string | null; country: string | null; institution: string | null; bio: string | null } | null;
  pitch: { url: string; transcript: string; duration: number } | null;
  evidence: ProfileEvidence[];
  updates: { id: string; body: string; created_at: string }[];
  lastActivity: string | null;
};

/**
 * Everything a founder profile shows, read as the person looking, so the
 * database decides what they may see. Returns null when the venture is not
 * visible to them, which looks the same as a venture that does not exist.
 */
export async function loadVentureProfile(supabase: SupabaseClient, ventureId: string): Promise<VentureProfile | null> {
  const venture = await supabase
    .from("ventures")
    .select("id, founder_id, name, sector, stage, country, description, website, published_at")
    .eq("id", ventureId)
    .maybeSingle();
  if (!venture.data) return null;
  const [founder, pitch, evidence, updates] = await Promise.all([
    supabase.from("public_profiles").select("full_name, city, country, institution, bio").eq("user_id", venture.data.founder_id).maybeSingle(),
    supabase.from("pitches").select("storage_path, transcript, duration_seconds, updated_at").eq("venture_id", ventureId).maybeSingle(),
    supabase.rpc("venture_evidence", { p_venture: ventureId }),
    supabase.from("venture_updates").select("id, body, created_at").eq("venture_id", ventureId).order("created_at", { ascending: false }).limit(20),
  ]);
  const signed = pitch.data ? await supabase.storage.from("pitches").createSignedUrl(pitch.data.storage_path, 3600) : null;
  const ev = ((evidence.data ?? []) as Record<string, unknown>[])
    .filter((e) => isShownStatus(e.shown_status))
    .map((e) => ({
      id: String(e.id),
      category: String(e.category),
      label: String(e.label),
      summary: (e.summary as string | null) ?? null,
      status: e.shown_status as ShownStatus,
      publicNote: (e.public_note as string | null) ?? null,
      reviewedAt: (e.reviewed_at as string | null) ?? null,
      createdAt: String(e.created_at),
    }));
  const upd = updates.data ?? [];
  const dates = [venture.data.published_at, pitch.data?.updated_at, upd[0]?.created_at, ...ev.map((e) => e.createdAt)].filter(Boolean) as string[];
  const { founder_id: _founder, ...v } = venture.data;
  return {
    venture: v,
    founder: founder.data ?? null,
    pitch: pitch.data && signed?.data?.signedUrl ? { url: signed.data.signedUrl, transcript: pitch.data.transcript, duration: Number(pitch.data.duration_seconds) } : null,
    evidence: ev,
    updates: upd,
    lastActivity: dates.sort().at(-1) ?? null,
  };
}
