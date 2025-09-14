import Link from 'next/link';

export default function Home() {
  return (
    <main style={{ maxWidth: 720, margin: '40px auto', padding: '0 16px' }}>
      <h1>Read The Game — Frontend Stub</h1>
      <p>
        This is a minimal Next.js stub. Provide an episode UUID or GUID in the URL to view a transcript.
      </p>
      <p>Example: <code>/episodes/00000000-0000-0000-0000-000000000000</code></p>
      <p>
        Once your pipeline writes records into Supabase, navigate to{' '}
        <Link href="/episodes/your-episode-id">/episodes/your-episode-id</Link>.
      </p>
    </main>
  );
}