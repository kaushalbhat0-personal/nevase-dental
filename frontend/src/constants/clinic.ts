export const CLINIC = {
  name: "Nevase's Multispeciality Dental Clinic",
  shortName: 'Nevase Dental',
  tagline: 'Advanced Dental Care, Close to Home',
  address: 'Besides Vaibhav Medical Store, Jadhav Nagar, Vadgaon Budruk, Pune 411041',
  phone: '+918805606018',
  phoneDisplay: '088056 06018',
  whatsappNumber: '918805606018',
  hours: 'Mon–Sat: 9:00 AM – 1:00 PM | 5:00 PM – 9:00 PM',
  googleMapsEmbed: 'https://maps.google.com/maps?q=Vadgaon+Budruk+Pune&output=embed',
} as const;

export const WHATSAPP_URL = `https://wa.me/${CLINIC.whatsappNumber}?text=Hi%2C%20I%20would%20like%20to%20book%20an%20appointment`;

export function bookingWhatsAppUrl(opts: { name: string; phone: string; service: string; date: string; message: string }) {
  const text = `Hi, I want to book an appointment.%0AName: ${encodeURIComponent(opts.name)}%0APhone: ${encodeURIComponent(opts.phone)}%0AService: ${encodeURIComponent(opts.service)}%0ADate: ${encodeURIComponent(opts.date)}%0AMessage: ${encodeURIComponent(opts.message)}`;
  return `https://wa.me/${CLINIC.whatsappNumber}?text=${text}`;
}

export const SERVICES = [
  { icon: '🦷', title: 'General Dentistry', desc: 'Checkups, cleanings, fillings & preventive care' },
  { icon: '🔬', title: 'Root Canal Treatment', desc: 'Painless RCT with modern rotary endodontics' },
  { icon: '✨', title: 'Teeth Whitening', desc: 'Professional bleaching for a brighter smile' },
  { icon: '🦾', title: 'Dental Implants', desc: 'Permanent titanium tooth replacement' },
  { icon: '😁', title: 'Orthodontics / Braces', desc: 'Metal, ceramic & invisible aligners' },
  { icon: '👑', title: 'Crowns & Bridges', desc: 'Restore damaged or missing teeth' },
  { icon: '🧒', title: 'Pediatric Dentistry', desc: 'Gentle, child-friendly dental care' },
  { icon: '💎', title: 'Dental Veneers', desc: 'Porcelain laminates for a perfect smile' },
  { icon: '🩺', title: 'Oral Surgery', desc: 'Extractions, biopsies & minor surgical procedures' },
  { icon: '🛡️', title: 'Gum Treatment', desc: 'Scaling, root planing & periodontal therapy' },
  { icon: '🫧', title: 'Scaling & Polishing', desc: 'Professional deep cleaning & stain removal' },
  { icon: '🦷', title: 'Dentures', desc: 'Full & partial dentures — comfortable fit' },
];

export const SERVICES_SELECT = [
  { value: 'general-dentistry', label: 'General Dentistry' },
  { value: 'root-canal', label: 'Root Canal Treatment' },
  { value: 'teeth-whitening', label: 'Teeth Whitening' },
  { value: 'implants', label: 'Dental Implants' },
  { value: 'orthodontics', label: 'Orthodontics / Braces' },
  { value: 'crowns-bridges', label: 'Crowns & Bridges' },
  { value: 'pediatric', label: 'Pediatric Dentistry' },
  { value: 'veneers', label: 'Dental Veneers' },
  { value: 'oral-surgery', label: 'Oral Surgery' },
  { value: 'gum-treatment', label: 'Gum Treatment' },
  { value: 'scaling', label: 'Scaling & Polishing' },
  { value: 'dentures', label: 'Dentures' },
];
