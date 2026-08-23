"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useProcess } from "../../context/ProcessContext";
import DomainIcon from "../shell/DomainIcon";

export default function DomainGallery() {
  const { domains, setSelectedDomain } = useProcess();
  const router = useRouter();

  const pick = (name: string) => {
    setSelectedDomain(name);
    router.push("/review");
  };

  return (
    <div className="panel">
      <div className="panel-title">
        Document Types
        <span className="font-normal normal-case tracking-normal text-muted">
          · one engine, many domains — more added over time
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
        {domains.map((d) => (
          <button
            key={d.name}
            onClick={() => pick(d.name)}
            className="group flex flex-col gap-2 rounded-xl border border-line/20 bg-white/[0.02] p-3 text-left transition-all hover:border-gold/50 hover:bg-gold/[0.05]"
          >
            <div className="flex items-center justify-between">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-violet/15 text-violet">
                <DomainIcon name={d.icon} className="h-4 w-4" />
              </span>
              <ArrowRight className="h-3.5 w-3.5 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
            </div>
            <div>
              <div className="text-sm font-semibold">{d.label}</div>
              <div className="mt-0.5 text-[11px] leading-snug text-muted">{d.description}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
