import Link from "next/link";

export default function NotFound() {
  return (
    <div className="text-center py-20">
      <div className="text-6xl font-mono text-muted mb-4">404</div>
      <Link href="/" className="text-accent">
        Back to winners
      </Link>
    </div>
  );
}
