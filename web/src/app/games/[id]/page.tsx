import GameReviewClient from "./review-client";

export default async function GameReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <GameReviewClient gameId={id} />;
}
