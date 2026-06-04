import { Star, ChevronRight } from 'lucide-react';
import type { PublicTenantDoctorBrief } from '../../types';

interface DoctorCardProps {
  doctor: PublicTenantDoctorBrief;
  onViewProfile?: (doctorId: string) => void;
}

function initials(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase();
}

export default function DoctorCard({ doctor, onViewProfile }: DoctorCardProps) {
  return (
    <div className="bg-white rounded-2xl p-8 text-center shadow-sm hover:shadow-lg transition-all duration-300 border border-gray-100 hover:border-[#0EA5E9]/20">
      <div className="w-28 h-28 mx-auto mb-5 rounded-full bg-gradient-to-br from-[#0EA5E9]/10 to-[#0284C7]/10 flex items-center justify-center">
        <span className="text-2xl font-bold text-[#0EA5E9]">
          {initials(doctor.name)}
        </span>
      </div>
      <h3 className="text-xl font-semibold text-[#0F172A]">{doctor.name}</h3>
      {doctor.specialization && (
        <span className="inline-block mt-2 px-3 py-1 bg-[#0EA5E9]/10 text-[#0EA5E9] text-xs font-medium rounded-full">
          {doctor.specialization}
        </span>
      )}
      {doctor.rating_average > 0 && (
        <div className="flex items-center justify-center gap-1 mt-3">
          <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
          <span className="text-sm font-medium text-[#1E293B]">
            {doctor.rating_average.toFixed(1)}
          </span>
          <span className="text-xs text-[#1E293B]/50">
            ({doctor.review_count})
          </span>
        </div>
      )}
      {onViewProfile && (
        <button
          onClick={() => onViewProfile(doctor.id)}
          className="mt-5 inline-flex items-center gap-1 px-5 py-2 rounded-lg text-sm font-medium text-[#0EA5E9] bg-[#0EA5E9]/5 hover:bg-[#0EA5E9]/10 transition-colors"
        >
          View Profile <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
