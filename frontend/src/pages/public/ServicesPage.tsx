import { SERVICES } from '../../constants/clinic';
import { CheckCircle } from 'lucide-react';

export default function ServicesPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="bg-gradient-to-br from-sky-50 via-white to-white py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-sm font-semibold text-[#0EA5E9] tracking-widest uppercase mb-3">
            What We Offer
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold text-[#0F172A]">
            Comprehensive Dental Care
          </h1>
          <p className="mt-4 text-lg text-[#1E293B]/60 max-w-2xl mx-auto">
            From routine checkups to advanced cosmetic procedures — we have
            specialist doctors for every dental need under one roof.
          </p>
        </div>
      </section>

      {/* Services grid */}
      <section className="py-16 sm:py-24 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {SERVICES.map((s) => (
              <div
                key={s.title}
                className="group bg-white rounded-2xl p-6 sm:p-8 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border border-gray-100 hover:border-[#0EA5E9]/30"
              >
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-xl bg-[#0EA5E9]/10 flex items-center justify-center text-3xl shrink-0 group-hover:bg-[#0EA5E9]/20 transition-colors">
                    {s.icon}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-lg font-semibold text-[#0F172A]">{s.title}</h3>
                    <p className="mt-2 text-sm text-[#1E293B]/60 leading-relaxed">{s.desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 sm:py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A]">Not Sure What You Need?</h2>
          <p className="mt-4 text-lg text-[#1E293B]/60 max-w-xl mx-auto">
            Book a consultation and we'll assess your dental health
            and recommend the best treatment plan.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <a
              href={`https://wa.me/918805606018?text=Hi%2C%20I%20want%20to%20book%20an%20appointment`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-base font-semibold text-white bg-[#0EA5E9] hover:bg-[#0284C7] shadow-lg shadow-[#0EA5E9]/25 transition-all hover:shadow-xl hover:scale-[1.02]"
            >
              <CheckCircle className="w-5 h-5" />
              Book a Consultation
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
