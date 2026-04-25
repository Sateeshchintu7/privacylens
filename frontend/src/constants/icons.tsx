/**
 * icons.tsx
 * Centralised SVG icon mapping for data categories.
 * Uses Lucide React — renders identically on all platforms.
 * Replaces emoji which render differently on Windows/Mac/Android/iOS.
 */
import type { ReactNode } from 'react'
import {
  Package,
  Share2,
  CheckCircle,
  Archive,
  Lock,
  PenLine,
  Cookie,
  Baby,
  Globe,
  Target,
  AlertTriangle,
  Mail,
  Bot,
  DollarSign,
  ScanFace,
  ShieldOff,
  Brain,
  ShieldAlert,
  FileText,
  MapPin,
  AtSign,
  User,
  Smartphone,
  CreditCard,
  Heart,
  Camera,
  Mic,
  Monitor,
  Wifi,
} from 'lucide-react'

export const CATEGORY_ICONS: Record<string, ReactNode> = {
  data_collection:           <Package       size={18} />,
  third_party_sharing:       <Share2        size={18} />,
  user_rights:               <CheckCircle   size={18} />,
  retention_period:          <Archive       size={18} />,
  data_security:             <Lock          size={18} />,
  consent_mechanism:         <PenLine       size={18} />,
  cookies_tracking:          <Cookie        size={18} />,
  children_data:             <Baby          size={18} />,
  cross_border_transfer:     <Globe         size={18} />,
  purpose_limitation:        <Target        size={18} />,
  breach_notification:       <AlertTriangle size={18} />,
  contact_info:              <Mail          size={18} />,
  automated_decision_making: <Bot           size={18} />,
  data_sale_vs_sharing:      <DollarSign    size={18} />,
  biometric_data:            <ScanFace      size={18} />,
  gpc_signal_honoring:       <ShieldOff     size={18} />,
  ai_system_disclosure:      <Brain         size={18} />,
  sensitive_data_categories: <ShieldAlert   size={18} />,
}

export const DEFAULT_ICON: ReactNode = <FileText size={18} />

export const DATA_TYPE_ICONS: Record<string, ReactNode> = {
  'location':   <MapPin     size={13} />,
  'gps':        <MapPin     size={13} />,
  'email':      <AtSign     size={13} />,
  'name':       <User       size={13} />,
  'phone':      <Smartphone size={13} />,
  'payment':    <CreditCard size={13} />,
  'health':     <Heart      size={13} />,
  'photo':      <Camera     size={13} />,
  'voice':      <Mic        size={13} />,
  'device':     <Monitor    size={13} />,
  'ip address': <Wifi       size={13} />,
}

export function getDataTypeIcons(text: string): ReactNode[] {
  const t = text.toLowerCase()
  return Object.entries(DATA_TYPE_ICONS)
    .filter(([keyword]) => t.includes(keyword))
    .map(([, icon]) => icon)
    .slice(0, 4)
}
