import Image from "next/image";

export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-500 to-purple-600">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-4">
          Welcome to AI Coach
        </h1>
        <p className="text-lg text-white/80">
          Your personal development partner
        </p>
      </div>
    </main>
  );
}
