import { MapPin, Phone, Clock, ArrowRight } from 'lucide-react';
import { CLINIC, WHATSAPP_URL } from '../../constants/clinic';

export default function ContactPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="bg-gradient-to-br from-sky-50 via-white to-white py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-sm font-semibold text-[#0EA5E9] tracking-widest uppercase mb-3">
            Get in Touch
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold text-[#0F172A]">Contact Us</h1>
          <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">
            We're here to help. Reach out to us anytime.
          </p>
        </div>
      </section>

      {/* Contact info + map */}
      <section className="py-16 sm:py-24 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-10 items-start">
            {/* Left — contact details */}
            <div className="space-y-6">
              <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-gray-100">
                <h2 className="text-2xl font-bold text-[#0F172A] mb-6">{CLINIC.shortName}</h2>
                <div className="space-y-5">
                  <div className="flex items-start gap-4">
                    <MapPin className="w-6 h-6 text-[#0EA5E9] shrink-0 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-[#0F172A]">Address</h3>
                      <p className="text-sm text-[#1E293B]/60 mt-1">{CLINIC.address}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4">
                    <Phone className="w-6 h-6 text-[#0EA5E9] shrink-0 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-[#0F172A]">Phone</h3>
                      <a
                        href={`tel:${CLINIC.phone}`}
                        className="text-sm text-[#0EA5E9] hover:underline mt-1 block"
                      >
                        {CLINIC.phoneDisplay}
                      </a>
                    </div>
                  </div>
                  <div className="flex items-start gap-4">
                    <Clock className="w-6 h-6 text-[#0EA5E9] shrink-0 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-[#0F172A]">Timings</h3>
                      <p className="text-sm text-[#1E293B]/60 mt-1">{CLINIC.hours}</p>
                    </div>
                  </div>
                </div>
              </div>

              <a
                href={WHATSAPP_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full py-4 rounded-xl text-base font-semibold text-white bg-[#25D366] hover:bg-[#1DA851] transition-all shadow-lg hover:shadow-xl"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
                Chat on WhatsApp
                <ArrowRight className="w-5 h-5" />
              </a>
            </div>

            {/* Right — map */}
            <div className="rounded-2xl overflow-hidden shadow-sm border border-gray-100 h-[400px] lg:h-[520px]">
              <iframe
                title="Nevase Dental Location"
                src={CLINIC.googleMapsEmbed}
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
