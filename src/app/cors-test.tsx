import { useEffect, useState } from 'react';

export default function DiagnosticCorsTest() {
  const [result, setResult] = useState<string>('⏳ Test en cours...');

  useEffect(() => {
    const testCORS = async () => {
      try {
        const res = await fetch('https://fkavtsofmglifzalclyn.supabase.co/rest/v1/posts', {
          method: 'GET',
          headers: {
            apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!}`,
            Prefer: 'return=minimal',
          },
        });

        if (!res.ok) {
          setResult(`❌ Erreur HTTP ${res.status} - ${res.statusText}`);
        } else {
          setResult(`✅ Succès HTTP ${res.status}`);
        }
      } catch (err: any) {
        setResult(`🚨 Erreur CORS ou réseau : ${err.message || err.toString()}`);
      }
    };

    testCORS();
  }, []);

  return (
    <div className="p-6 text-sm font-mono bg-orange-50 text-orange-800 rounded-xl shadow">
      <h2 className="text-lg font-bold mb-4">🧪 Test CORS Supabase</h2>
      <p>{result}</p>
    </div>
  );
}
