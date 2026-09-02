"use client";

import {
  Award,
  Banknote,
  ClipboardList,
  FileDigit,
  FileLock2,
  FileScan,
  FileSignature,
  FileText,
  GraduationCap,
  HandCoins,
  HeartPulse,
  IdCard,
  KeyRound,
  Landmark,
  MailCheck,
  PackageOpen,
  Pill,
  Plug,
  ReceiptText,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Ship,
  ShoppingBag,
  Stethoscope,
  Truck,
  UserRound,
  Users,
  Wallet,
} from "lucide-react";

const MAP: Record<string, typeof FileText> = {
  // documents
  ReceiptText, ShoppingBag, UserRound, ClipboardList, FileSignature, IdCard,
  Landmark, FileScan, Wallet, FileDigit, FileText, Banknote, HandCoins,
  ShieldAlert, Stethoscope, Pill, MailCheck, Award, Plug, FileLock2, KeyRound,
  Ship, PackageOpen, Truck, GraduationCap,
  // industries
  HeartPulse, Users, ShieldCheck, Scale,
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
