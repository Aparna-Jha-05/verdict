"use client";

import {
  ClipboardList,
  FileScan,
  FileSignature,
  FileText,
  IdCard,
  Landmark,
  ReceiptText,
  ShoppingBag,
  UserRound,
} from "lucide-react";

const MAP: Record<string, typeof FileText> = {
  ReceiptText,
  ShoppingBag,
  UserRound,
  ClipboardList,
  FileSignature,
  IdCard,
  Landmark,
  FileScan,
};

export default function DomainIcon({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  const Icon = MAP[name] || FileText;
  return <Icon className={className} />;
}
