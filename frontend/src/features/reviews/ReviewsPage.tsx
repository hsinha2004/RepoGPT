import React from "react";
import { useParams } from "react-router";

export const ReviewsPage: React.FC = () => {
  const { repoId } = useParams();
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Pull Request Reviews</h1>
      <p className="text-sm text-[#a1a1aa]">Repository: {repoId}</p>
    </div>
  );
};
