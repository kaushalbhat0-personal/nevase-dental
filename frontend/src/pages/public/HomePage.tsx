import { useState } from 'react';
import { CheckCircle, Star, ChevronRight, MapPin, Phone, Clock, ArrowRight } from 'lucide-react';

const WHATSAPP_NUMBER = '918805606018';

const services = [
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

const servicesSelect = [
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

function ToothSVG() {
  return (
    <svg viewBox="0 0 200 240" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full drop-shadow-xl animate-float">
      <defs>
        <linearGradient id="tooth-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#F0F9FF" />
          <stop offset="100%" stopColor="#E0F2FE" />
        </linearGradient>
        <linearGradient id="tooth-shine" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="white" stopOpacity="0.8" />
          <stop offset="100%" stopColor="white" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M100 20 C80 20 55 35 50 65 C45 85 42 110 45 135 C48 155 55 175 65 190 C72 200 80 210 90 215 C95 218 98 220 100 220 C102 220 105 218 110 215 C120 210 128 200 135 190 C145 175 152 155 155 135 C158 110 155 85 150 65 C145 35 120 20 100 20Z"
        fill="url(#tooth-grad)"
        stroke="#BAE6FD"
        strokeWidth="2"
        className="animate-tooth-pulse"
      />
      <path
        d="M85 50 C85 50 90 70 85 90 C80 110 75 120 75 120"
        stroke="url(#tooth-shine)"
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
        opacity="0.6"
      />
      <path
        d="M95 45 C100 60 100 80 95 95"
        stroke="url(#tooth-shine)"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        opacity="0.4"
      />
      <path
        d="M65 140 C70 150 75 160 80 165"
        stroke="#BAE6FD"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
        opacity="0.5"
      />
      <path
        d="M135 140 C130 150 125 160 120 165"
        stroke="#BAE6FD"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
        opacity="0.5"
      />
      <path
        d="M70 100 L130 100 M75 110 L125 110"
        stroke="#BAE6FD"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        opacity="0.4"
      />
    </svg>
  );
}

const testimonials = [
  { name: 'Rahul M., Pune', text: 'Completely painless root canal. The doctor was patient and explained everything. Highly recommend!', rating: 5 },
  { name: 'Priya S., Pune', text: 'Best dental clinic for kids in Vadgaon Budruk. My 5 year old actually enjoys visiting the dentist now.', rating: 5 },
  { name: 'Amit K., Pune', text: 'Fixed my smile with braces in 18 months. Life changing results. Thank you Nevase Dental!', rating: 5 },
];

export default function HomePage() {
  const [form, setForm] = useState({ name: '', phone: '', service: '', date: '', message: '' });
  const [submitted, setSubmitted] = useState(false);

  const handleBookingSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const waText = `Hi, I want to book an appointment.%0AName: ${encodeURIComponent(form.name)}%0APhone: ${encodeURIComponent(form.phone)}%0AService: ${encodeURIComponent(form.service)}%0ADate: ${encodeURIComponent(form.date)}%0AMessage: ${encodeURIComponent(form.message)}`;
    window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${waText}`, '_blank');
    setSubmitted(true);
  };

  return (
    <div>
      {/* ── HERO ── */}
      <section className="relative min-h-screen flex items-center overflow-hidden bg-gradient-to-br from-sky-50 via-white to-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(14,165,233,0.08),transparent_70%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(14,165,233,0.05),transparent_50%)]" />

        <div className="relative max-w-7xl mx-auto px-4 w-full">
          <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16 py-20 lg:py-24">
            {/* LEFT: 60% */}
            <div className="flex-1 lg:flex-[1.5] text-center lg:text-left">
              <div className="inline-flex items-center gap-2 bg-[#0EA5E9]/10 text-[#0EA5E9] text-sm font-medium px-4 py-1.5 rounded-full mb-6">
                <Star className="w-4 h-4 fill-[#0EA5E9]" />
                Trusted by 500+ patients in Pune
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight tracking-tight">
                <span className="text-[#0F172A] font-normal">Smile Brighter with</span>
                <br />
                <span className="bg-gradient-to-r from-[#0EA5E9] to-[#0284C7] bg-clip-text text-transparent">
                  Expert Dental Care
                </span>
              </h1>

              <p className="mt-6 text-lg sm:text-xl text-[#1E293B]/70 max-w-xl leading-relaxed lg:mx-0 mx-auto">
                Multispeciality dental clinic at Vadgaon Budruk, Pune.
                Modern treatments, painless procedures, caring doctors.
              </p>

              {/* CTAs */}
              <div className="mt-8 flex flex-wrap items-center gap-4 justify-center lg:justify-start">
                <a
                  href={`https://wa.me/${WHATSAPP_NUMBER}?text=Hi%2C%20I%20want%20to%20book%20an%20appointment%20at%20Nevase%20Dental`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-base font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] shadow-lg shadow-[#0EA5E9]/25 transition-all hover:shadow-xl hover:scale-[1.02]"
                >
                  Book Appointment
                  <ArrowRight className="w-5 h-5" />
                </a>
                <a
                  href={`https://wa.me/${WHATSAPP_NUMBER}?text=Hi%2C%20I%20want%20to%20book%20an%20appointment%20at%20Nevase%20Dental`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-base font-semibold text-white bg-[#25D366] hover:bg-[#1DA851] shadow-lg shadow-[#25D366]/25 transition-all hover:shadow-xl hover:scale-[1.02]"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                  Chat on WhatsApp
                </a>
              </div>

              {/* Trust pills */}
              <div className="mt-8 flex flex-wrap items-center gap-6 text-sm text-[#1E293B]/60 justify-center lg:justify-start">
                <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-green-500" /> Painless Treatment</span>
                <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-green-500" /> Same Day Appointments</span>
                <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-green-500" /> All Age Groups</span>
              </div>
            </div>

            {/* RIGHT: 40% — animated tooth + floating cards */}
            <div className="flex-1 relative hidden lg:block">
              <div className="relative w-full max-w-md mx-auto">
                <div className="absolute inset-0 bg-[#0EA5E9] opacity-[0.04] rounded-full blur-3xl scale-150" />
                <div className="relative">
                  <ToothSVG />
                </div>

                {/* Floating stat cards */}
                <div className="absolute -top-4 -right-4 bg-white rounded-2xl shadow-lg px-5 py-3 border border-gray-100 animate-float-delayed">
                  <p className="text-2xl font-bold text-[#0EA5E9]">500+</p>
                  <p className="text-xs text-[#1E293B]/60">Happy Patients</p>
                </div>
                <div className="absolute -bottom-2 -left-6 bg-white rounded-2xl shadow-lg px-5 py-3 border border-gray-100 animate-float-slow">
                  <p className="text-2xl font-bold text-[#0EA5E9]">10+</p>
                  <p className="text-xs text-[#1E293B]/60">Years Experience</p>
                </div>
                <div className="absolute top-1/3 -left-8 bg-white rounded-2xl shadow-lg px-5 py-3 border border-gray-100 animate-float">
                  <p className="text-2xl font-bold text-[#0EA5E9]">5★</p>
                  <p className="text-xs text-[#1E293B]/60">Google Rating</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── STATS BAR ── */}
      <section className="bg-[#0EA5E9] py-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center text-white">
            <div>
              <p className="text-3xl sm:text-4xl font-bold">500+</p>
              <p className="text-white/80 text-sm mt-1">Happy Patients</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-bold">5.0</p>
              <p className="text-white/80 text-sm mt-1">Google Rating</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-bold">12+</p>
              <p className="text-white/80 text-sm mt-1">Treatments</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-bold">10+</p>
              <p className="text-white/80 text-sm mt-1">Years Experience</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── SERVICES ── */}
      <section id="services" className="py-20 sm:py-28 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-[#0EA5E9] tracking-widest uppercase mb-3">What We Offer</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Comprehensive Dental Care</h2>
            <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">From routine checkups to advanced cosmetic procedures</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {services.map((s) => (
              <div
                key={s.title}
                className="group bg-white rounded-2xl p-6 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border border-gray-100 hover:border-[#0EA5E9]/30"
              >
                <div className="w-12 h-12 rounded-xl bg-[#0EA5E9]/10 flex items-center justify-center text-2xl mb-4 group-hover:bg-[#0EA5E9]/20 transition-colors">
                  {s.icon}
                </div>
                <h3 className="text-base font-semibold text-[#0F172A]">{s.title}</h3>
                <p className="mt-2 text-sm text-[#1E293B]/60 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── WHY CHOOSE US ── */}
      <section id="about" className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-[#0EA5E9] tracking-widest uppercase mb-3">Why Choose Us</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Why Patients Choose Nevase's Dental</h2>
          </div>
          <div className="grid lg:grid-cols-2 gap-8">
            {/* LEFT — big feature */}
            <div className="bg-gradient-to-br from-[#F0F9FF] to-white rounded-2xl p-8 sm:p-10 border border-[#0EA5E9]/10 shadow-sm">
              <div className="w-16 h-16 rounded-2xl bg-[#0EA5E9]/10 flex items-center justify-center text-4xl mb-5">
                🏥
              </div>
              <h3 className="text-2xl font-bold text-[#0F172A]">Multispeciality Under One Roof</h3>
              <p className="mt-4 text-[#1E293B]/70 leading-relaxed">
                From routine cleanings to complex root canals, implants, and cosmetic procedures — 
                we have specialist doctors for every dental need. No more running between clinics.
              </p>
              <ul className="mt-6 space-y-3">
                {[
                  'General Dentistry & Checkups',
                  'Root Canal & Endodontics',
                  'Orthodontics & Braces',
                  'Implantology & Oral Surgery',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-[#1E293B]/70">
                    <CheckCircle className="w-4 h-4 text-[#0EA5E9] shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* RIGHT — 3 smaller features */}
            <div className="space-y-5">
              <div className="bg-white rounded-2xl p-6 sm:p-8 border border-gray-100 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-start gap-5">
                  <div className="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center text-2xl shrink-0">💉</div>
                  <div>
                    <h3 className="text-lg font-semibold text-[#0F172A]">Painless Procedures</h3>
                    <p className="mt-1 text-sm text-[#1E293B]/60">Latest anaesthesia techniques ensure zero discomfort during treatment.</p>
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-2xl p-6 sm:p-8 border border-gray-100 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-start gap-5">
                  <div className="w-12 h-12 rounded-xl bg-orange-50 flex items-center justify-center text-2xl shrink-0">🕐</div>
                  <div>
                    <h3 className="text-lg font-semibold text-[#0F172A]">Flexible Timings</h3>
                    <p className="mt-1 text-sm text-[#1E293B]/60">Morning and evening slots available to fit your busy schedule.</p>
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-2xl p-6 sm:p-8 border border-gray-100 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-start gap-5">
                  <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center text-2xl shrink-0">📍</div>
                  <div>
                    <h3 className="text-lg font-semibold text-[#0F172A]">Prime Location — Vadgaon Budruk</h3>
                    <p className="mt-1 text-sm text-[#1E293B]/60">Easily accessible, with ample parking and convenient public transport.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── DOCTORS ── */}
      <section id="doctors" className="py-20 sm:py-28 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-[#0EA5E9] tracking-widest uppercase mb-3">Our Team</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Meet Our Specialists</h2>
            <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">Experienced dental professionals dedicated to your smile</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-8 max-w-3xl mx-auto">
            {[1, 2].map((i) => (
              <div key={i} className="bg-white rounded-2xl p-8 text-center shadow-sm hover:shadow-lg transition-all duration-300 border border-gray-100 hover:border-[#0EA5E9]/20">
                <div className="w-28 h-28 mx-auto mb-5 rounded-full bg-gray-100 flex items-center justify-center">
                  <svg className="w-16 h-16 text-gray-400" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                </div>
                <h3 className="text-xl font-semibold text-[#0F172A]">Dr. [Name]</h3>
                <span className="inline-block mt-2 px-3 py-1 bg-[#0EA5E9]/10 text-[#0EA5E9] text-xs font-medium rounded-full">
                  Dental Specialist
                </span>
                <p className="mt-4 text-sm text-[#1E293B]/60">Experienced professional dedicated to your dental health.</p>
                <button className="mt-5 inline-flex items-center gap-1 px-5 py-2 rounded-lg text-sm font-medium text-[#0EA5E9] bg-[#0EA5E9]/5 hover:bg-[#0EA5E9]/10 transition-colors">
                  View Profile <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
          <p className="text-center mt-8 text-sm text-[#1E293B]/40 italic">{/* TODO: fetch from GET /api/v1/doctors */}</p>
        </div>
      </section>

      {/* ── TESTIMONIALS ── */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-[#0EA5E9] tracking-widest uppercase mb-3">Testimonials</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">What Our Patients Say</h2>
            <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">Real stories from real patients</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <div key={t.name} className="relative bg-[#F8FAFC] rounded-2xl p-8 border border-gray-100 hover:shadow-md transition-all duration-300">
                <div className="absolute -top-3 -left-2 text-5xl text-[#0EA5E9]/10 font-serif leading-none">"</div>
                <div className="flex gap-1 mb-4">
                  {Array.from({ length: t.rating }).map((_, i) => (
                    <Star key={i} className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-[#1E293B]/80 leading-relaxed mb-4 relative z-10">"{t.text}"</p>
                <p className="font-medium text-sm text-[#0F172A]">— {t.name}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── BOOK APPOINTMENT ── */}
      <section id="book" className="py-20 sm:py-28 bg-gradient-to-br from-[#0EA5E9]/5 to-[#0284C7]/5">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid lg:grid-cols-5 gap-10 items-start">
            {/* LEFT — form */}
            <div className="lg:col-span-3">
              <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Book Your Appointment</h2>
              <p className="mt-3 text-[#1E293B]/60">Fill in your details and we'll confirm within minutes</p>

              {submitted ? (
                <div className="mt-8 bg-white rounded-2xl p-8 shadow-sm border border-gray-100 text-center max-w-lg">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-500" />
                  </div>
                  <h3 className="text-xl font-semibold text-[#0F172A]">Message Sent! ✅</h3>
                  <p className="mt-2 text-[#1E293B]/60">We'll get back to you shortly on WhatsApp.</p>
                  <a
                    href={`https://wa.me/${WHATSAPP_NUMBER}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-6 inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-[#25D366] hover:bg-[#1DA851] transition-colors"
                  >
                    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                    Chat on WhatsApp
                  </a>
                </div>
              ) : (
                <form onSubmit={handleBookingSubmit} className="mt-8 bg-white rounded-2xl p-8 shadow-sm border border-gray-100 space-y-5 max-w-lg">
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Full Name *</label>
                      <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm" placeholder="Your name" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Phone Number *</label>
                      <input type="tel" required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm" placeholder="Your phone number" />
                    </div>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Select Service</label>
                      <select value={form.service} onChange={(e) => setForm({ ...form, service: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm bg-white">
                        <option value="">Select a service</option>
                        {servicesSelect.map((s) => (
                          <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Preferred Date</label>
                      <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Message (optional)</label>
                    <textarea rows={3} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm resize-none" placeholder="Any specific concerns..." />
                  </div>
                  <button type="submit" className="w-full py-3.5 rounded-xl text-base font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] transition-all shadow-lg shadow-[#0EA5E9]/25">
                    Request Appointment
                  </button>
                  <p className="text-center text-sm text-[#1E293B]/60">
                    Or call us directly:{' '}
                    <a href="tel:+918805606018" className="text-[#0EA5E9] font-medium hover:underline">088056 06018</a>
                  </p>
                </form>
              )}
            </div>

            {/* RIGHT — info box */}
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 space-y-6">
                <div className="flex items-start gap-4">
                  <MapPin className="w-6 h-6 text-[#0EA5E9] shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-[#0F172A]">Address</h3>
                    <p className="text-sm text-[#1E293B]/60 mt-1">Besides Vaibhav Medical Store, Jadhav Nagar, Vadgaon Budruk, Pune 411041</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <Phone className="w-6 h-6 text-[#0EA5E9] shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-[#0F172A]">Phone</h3>
                    <a href="tel:+918805606018" className="text-sm text-[#0EA5E9] hover:underline mt-1 block">088056 06018</a>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <Clock className="w-6 h-6 text-[#0EA5E9] shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-[#0F172A]">Timings</h3>
                    <p className="text-sm text-[#1E293B]/60 mt-1">Mon–Sat: 9:00 AM – 1:00 PM | 5:00 PM – 9:00 PM</p>
                  </div>
                </div>
                <a
                  href={`https://wa.me/${WHATSAPP_NUMBER}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm font-semibold text-white bg-[#25D366] hover:bg-[#1DA851] transition-colors"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                  Chat on WhatsApp
                </a>
              </div>

              {/* Google Maps embed */}
              <div className="rounded-2xl overflow-hidden shadow-sm border border-gray-100 h-[220px]">
                <iframe
                  title="Nevase Dental Location"
                  src="https://maps.google.com/maps?q=Vadgaon+Budruk+Pune&output=embed"
                  width="100%"
                  height="100%"
                  style={{ border: 0 }}
                  allowFullScreen
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
