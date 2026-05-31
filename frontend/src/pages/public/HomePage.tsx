import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle, ChevronRight, Star, Phone, MapPin, Clock } from 'lucide-react';

const WHATSAPP_NUMBER = '918805606018';
const WHATSAPP_URL = `https://wa.me/${WHATSAPP_NUMBER}?text=Hi%2C%20I%20want%20to%20book%20an%20appointment%20at%20Nevase%20Dental`;

const services = [
  { icon: '🦷', title: 'General Dentistry', desc: 'Checkups, cleanings, fillings' },
  { icon: '🔬', title: 'Root Canal Treatment', desc: 'Painless RCT with modern techniques' },
  { icon: '😁', title: 'Teeth Whitening', desc: 'Professional whitening treatments' },
  { icon: '🦾', title: 'Dental Implants', desc: 'Permanent tooth replacement' },
  { icon: '🔧', title: 'Orthodontics', desc: 'Braces and aligners for all ages' },
  { icon: '👑', title: 'Crowns & Bridges', desc: 'Restore damaged teeth' },
  { icon: '🧒', title: 'Pediatric Dentistry', desc: 'Gentle care for children' },
  { icon: '💎', title: 'Dental Veneers', desc: 'Cosmetic smile makeover' },
  { icon: '🩺', title: 'Oral Surgery', desc: 'Extractions and minor surgeries' },
  { icon: '🛡️', title: 'Gum Treatment', desc: 'Periodontal care' },
  { icon: '💫', title: 'Scaling & Polishing', desc: 'Professional cleaning' },
  { icon: '🦷', title: 'Dentures', desc: 'Full and partial dentures' },
];

const whyChooseUs = [
  { icon: '🏥', title: 'Multispeciality', desc: 'Multiple specialists under one roof' },
  { icon: '💉', title: 'Painless', desc: 'Latest anaesthesia techniques' },
  { icon: '🕐', title: 'Flexible Timings', desc: 'Morning and evening slots' },
  { icon: '📍', title: 'Prime Location', desc: 'Vadgaon Budruk, Pune' },
];

const testimonials = [
  { name: 'Rahul M., Pune', text: 'Completely painless root canal. Highly recommend!', rating: 5 },
  { name: 'Priya S., Pune', text: 'Best dental clinic for kids in Vadgaon Budruk.', rating: 5 },
  { name: 'Amit K., Pune', text: 'Fixed my smile with braces in 18 months.', rating: 5 },
];

const servicesList = [
  { value: 'general-dentistry', label: 'General Dentistry' },
  { value: 'root-canal', label: 'Root Canal Treatment' },
  { value: 'teeth-whitening', label: 'Teeth Whitening' },
  { value: 'implants', label: 'Dental Implants' },
  { value: 'orthodontics', label: 'Orthodontics' },
  { value: 'crowns-bridges', label: 'Crowns & Bridges' },
  { value: 'pediatric', label: 'Pediatric Dentistry' },
  { value: 'veneers', label: 'Dental Veneers' },
  { value: 'oral-surgery', label: 'Oral Surgery' },
  { value: 'gum-treatment', label: 'Gum Treatment' },
  { value: 'scaling', label: 'Scaling & Polishing' },
  { value: 'dentures', label: 'Dentures' },
];

export default function HomePage() {
  const [formData, setFormData] = useState({ name: '', phone: '', service: '', date: '', message: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (window.location.hash === '#about') {
      const el = document.getElementById('about');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch('/api/v1/appointments/public-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (res.ok) {
        setSubmitted(true);
      } else {
        const waText = `Hi, I want to book an appointment.%0AName: ${encodeURIComponent(formData.name)}%0APhone: ${encodeURIComponent(formData.phone)}%0AService: ${encodeURIComponent(formData.service)}%0ADate: ${encodeURIComponent(formData.date)}%0AMessage: ${encodeURIComponent(formData.message)}`;
        window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${waText}`, '_blank');
        setSubmitted(true);
      }
    } catch {
      const waText = `Hi, I want to book an appointment.%0AName: ${encodeURIComponent(formData.name)}%0APhone: ${encodeURIComponent(formData.phone)}%0AService: ${encodeURIComponent(formData.service)}%0ADate: ${encodeURIComponent(formData.date)}%0AMessage: ${encodeURIComponent(formData.message)}`;
      window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${waText}`, '_blank');
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      {/* ── HERO ── */}
      <section className="relative overflow-hidden bg-gradient-to-br from-sky-50 via-white to-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(14,165,233,0.08),transparent_70%)]" />
        <div className="relative max-w-7xl mx-auto px-4 py-20 sm:py-28 lg:py-36">
          <div className="max-w-3xl">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-[#0F172A] leading-tight tracking-tight">
              Advanced Dental Care in the Heart of Pune
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-[#1E293B]/70 max-w-2xl leading-relaxed">
              Multispeciality dental clinic serving Vadgaon Budruk and surrounding areas
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                to="/book"
                className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl text-base font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] shadow-lg shadow-[#0EA5E9]/25 transition-all hover:shadow-xl hover:scale-[1.02]"
              >
                Book Appointment
                <ChevronRight className="w-5 h-5" />
              </Link>
              <a
                href={WHATSAPP_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl text-base font-semibold text-white bg-[#25D366] hover:bg-[#1DA851] shadow-lg shadow-[#25D366]/25 transition-all hover:shadow-xl hover:scale-[1.02]"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                Chat on WhatsApp
              </a>
              <Link
                to="/login"
                className="text-sm font-medium text-[#1E293B]/60 hover:text-[#0EA5E9] transition-colors underline underline-offset-4"
              >
                Patient Login →
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-6 text-sm text-[#1E293B]/60">
              <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-green-500" /> Expert Dentists</span>
              <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-green-500" /> Modern Equipment</span>
              <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-green-500" /> Painless Treatment</span>
              <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-green-500" /> Flexible Timings</span>
            </div>
            <div className="mt-10 grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-8 border-t border-[#0EA5E9]/10 pt-8">
              {[
                { value: '500+', label: 'Happy Patients' },
                { value: '10+', label: 'Years Experience' },
                { value: '12+', label: 'Treatments' },
                { value: '5★', label: 'Rated' },
              ].map((stat) => (
                <div key={stat.label} className="text-center">
                  <div className="text-2xl sm:text-3xl font-bold text-[#0EA5E9]">{stat.value}</div>
                  <div className="text-xs sm:text-sm text-[#1E293B]/60 mt-1">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── SERVICES ── */}
      <section className="py-20 sm:py-28 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Our Services</h2>
            <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">Comprehensive dental care for the whole family</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {services.map((s) => (
              <div key={s.title} className="group bg-white rounded-2xl p-6 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border border-gray-100">
                <div className="text-4xl mb-4">{s.icon}</div>
                <h3 className="text-lg font-semibold text-[#0F172A]">{s.title}</h3>
                <p className="mt-2 text-sm text-[#1E293B]/60">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── WHY CHOOSE US ── */}
      <section id="about" className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Why Choose Nevase Dental?</h2>
            <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">We combine expertise with compassion for the best dental experience</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {whyChooseUs.map((w) => (
              <div key={w.title} className="text-center p-8 rounded-2xl bg-gradient-to-b from-[#F0F9FF] to-white border border-[#0EA5E9]/10 hover:shadow-lg transition-all duration-300">
                <div className="text-5xl mb-5">{w.icon}</div>
                <h3 className="text-lg font-semibold text-[#0F172A]">{w.title}</h3>
                <p className="mt-2 text-sm text-[#1E293B]/60">{w.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DOCTORS ── */}
      <section className="py-20 sm:py-28 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Meet Our Specialists</h2>
            <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">Experienced dental professionals dedicated to your smile</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-8 max-w-3xl mx-auto">
            {[1, 2].map((i) => (
              <div key={i} className="bg-white rounded-2xl p-8 text-center shadow-sm hover:shadow-lg transition-all duration-300 border border-gray-100">
                <svg className="w-24 h-24 mx-auto mb-5 text-gray-300" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                <h3 className="text-lg font-semibold text-[#0F172A]">Dr. [Name]</h3>
                <p className="text-sm text-[#1E293B]/60 mt-1">Dental Specialist</p>
                <button className="mt-4 text-sm font-medium text-[#0EA5E9] hover:text-[#0284C7] transition-colors">View Profile →</button>
              </div>
            ))}
          </div>
          <p className="text-center mt-8 text-sm text-[#1E293B]/40 italic">* Fetching from API... TODO: GET /api/v1/doctors</p>
        </div>
      </section>

      {/* ── TESTIMONIALS ── */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">What Our Patients Say</h2>
            <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">Real stories from real patients</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <div key={t.name} className="bg-[#F8FAFC] rounded-2xl p-8 border border-gray-100 hover:shadow-md transition-all duration-300">
                <div className="flex gap-1 mb-4">
                  {Array.from({ length: t.rating }).map((_, i) => (
                    <Star key={i} className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-[#1E293B]/80 leading-relaxed mb-4">"{t.text}"</p>
                <p className="font-medium text-sm text-[#0F172A]">— {t.name}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── BOOK APPOINTMENT ── */}
      <section className="py-20 sm:py-28 bg-gradient-to-br from-[#0EA5E9] to-[#0284C7]">
        <div className="max-w-4xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-white">Book Your Appointment</h2>
            <p className="mt-4 text-lg text-white/80">Schedule your visit today — we'll confirm within minutes</p>
          </div>
          {submitted ? (
            <div className="bg-white rounded-2xl p-10 text-center shadow-xl max-w-lg mx-auto">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-green-500" />
              </div>
              <h3 className="text-xl font-semibold text-[#0F172A]">Request Submitted!</h3>
              <p className="mt-2 text-[#1E293B]/60">We'll get back to you shortly. You can also message us directly on WhatsApp.</p>
              <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="mt-6 inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-[#25D366] hover:bg-[#1DA851] transition-colors">
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                Chat on WhatsApp
              </a>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="bg-white rounded-2xl p-8 sm:p-10 shadow-xl max-w-2xl mx-auto space-y-5">
              <div className="grid sm:grid-cols-2 gap-5">
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Full Name *</label>
                  <input type="text" required value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm" placeholder="Your name" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Phone *</label>
                  <input type="tel" required value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm" placeholder="Your phone number" />
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-5">
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Service</label>
                  <select value={formData.service} onChange={(e) => setFormData({ ...formData, service: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm bg-white">
                    <option value="">Select service</option>
                    {servicesList.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Preferred Date</label>
                  <input type="date" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-1.5">Message (optional)</label>
                <textarea rows={3} value={formData.message} onChange={(e) => setFormData({ ...formData, message: e.target.value })} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/20 outline-none transition-all text-sm resize-none" placeholder="Any specific concerns..." />
              </div>
              <button type="submit" disabled={submitting} className="w-full py-3.5 rounded-xl text-base font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] disabled:opacity-50 transition-all shadow-lg shadow-[#0EA5E9]/25">
                {submitting ? 'Submitting...' : 'Request Appointment'}
              </button>
              <p className="text-center text-sm text-[#1E293B]/60">Or chat directly on <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="text-[#25D366] font-medium hover:underline">WhatsApp</a></p>
            </form>
          )}
        </div>
      </section>

      {/* ── LOCATION ── */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Visit Us</h2>
            <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">Conveniently located in Vadgaon Budruk, Pune</p>
          </div>
          <div className="grid md:grid-cols-2 gap-10 items-start">
            <div className="space-y-6">
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
                  <p className="text-sm text-[#1E293B]/60 mt-1">Mon–Sat: 10:00 AM – 1:30 PM | 5:00 PM – 9:00 PM</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-3 pt-2">
                <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-[#25D366] hover:bg-[#1DA851] transition-colors">
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                  Chat on WhatsApp
                </a>
                <a href={`https://maps.google.com/maps?q=Vadgaon+Budruk+Pune`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-[#0EA5E9] bg-[#0EA5E9]/10 hover:bg-[#0EA5E9]/20 transition-colors">
                  <MapPin className="w-5 h-5" />
                  Get Directions
                </a>
              </div>
            </div>
            <div className="rounded-2xl overflow-hidden shadow-lg border border-gray-100 h-[350px]">
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
      </section>
    </div>
  );
}
