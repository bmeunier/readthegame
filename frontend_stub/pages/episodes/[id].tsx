import { GetServerSideProps } from 'next';
import Head from 'next/head';
import { supabase } from '@lib/supabaseClient';
import Transcript, { Segment } from '@components/Transcript';

type Props = {
  episodeId: string;
  title: string | null;
  segments: Segment[];
};

export default function EpisodePage({ episodeId, title, segments }: Props) {
  return (
    <main style={{ maxWidth: 860, margin: '40px auto', padding: '0 16px' }}>
      <Head>
        <title>{title ?? 'Episode'} — Read The Game</title>
      </Head>
      <h1 style={{ marginBottom: 8 }}>{title ?? 'Episode'}</h1>
      <p style={{ opacity: 0.7, marginTop: 0 }}>Episode ID: {episodeId}</p>

      <section style={{ marginTop: 24 }}>
        <h3>Transcript</h3>
        <Transcript segments={segments} />
      </section>
    </main>
  );
}

export const getServerSideProps: GetServerSideProps = async (ctx) => {
  const id = String(ctx.params?.id);

  // Lookup episode by ID (uuid or guid)
  // First: try id as uuid
  let episode = await supabase.from('episodes').select('id,title').eq('id', id).maybeSingle();

  if (!episode.data) {
    // Fallback: treat as GUID
    episode = await supabase.from('episodes').select('id,title').eq('guid', id).maybeSingle();
  }

  if (!episode.data) {
    return { notFound: true };
  }

  const { data: segs } = await supabase
    .from('segments')
    .select('start_seconds,end_seconds,speaker_global_id,text,confidence')
    .eq('episode_id', episode.data.id)
    .order('start_seconds', { ascending: true });

  const segments: Segment[] = (segs ?? []).map((s: any) => ({
    start_seconds: s.start_seconds,
    end_seconds: s.end_seconds,
    speaker_global_id: s.speaker_global_id,
    text: s.text,
    confidence: s.confidence ?? null,
  }));

  return {
    props: {
      episodeId: episode.data.id,
      title: episode.data.title ?? null,
      segments,
    },
  };
};