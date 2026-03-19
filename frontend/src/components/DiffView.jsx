import DiffMatchPatch from "diff-match-patch";

const dmp = new DiffMatchPatch();

export default function DiffView({ original, tailored }) {
  return (
    <div className="space-y-3">
      {original.map((orig, i) => {
        const diff = dmp.diff_main(orig, tailored[i] || "");
        dmp.diff_cleanupSemantic(diff);

        return (
          <div key={i} className="bg-zinc-800/50 rounded-md p-3 border border-white/5">
            <span className="text-xs text-zinc-500 mb-1 block">Bullet {i + 1}</span>
            <p className="text-sm leading-relaxed">
              {diff.map(([op, text], j) => {
                if (op === -1)
                  return (
                    <span key={j} className="bg-red-500/20 text-red-300 line-through">
                      {text}
                    </span>
                  );
                if (op === 1)
                  return (
                    <span key={j} className="bg-green-500/20 text-green-300">
                      {text}
                    </span>
                  );
                return <span key={j} className="text-zinc-300">{text}</span>;
              })}
            </p>
          </div>
        );
      })}
    </div>
  );
}
