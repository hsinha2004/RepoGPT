import React from "react";
import { useParams } from "react-router";

export const OverviewPage: React.FC = () => {
  const { repoId } = useParams();
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Repository Overview</h1>
      <p className="text-sm text-[#a1a1aa]">Viewing overview for repository ID: {repoId}</p>
    </div>
  );
};
