/**
 * VisitPreparationCard.tsx — Static/generic visit preparation reminders.
 *
 * These are GENERIC preparedness reminders, NOT medical recommendations.
 * No AI, no personalization, no clinical advice.
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { ClipboardList, FileText, Pill, MapPin } from 'lucide-react';
import {
  genericPreparationItems,
  getGroupedChecklist,
  preparationHeaderMessage,
  preparationFooterMessage,
  getCategoryLabel,
} from '@/utils/preparationChecklist';

const categoryIcons: Record<string, React.ReactNode> = {
  documents: <FileText className="h-4 w-4 text-blue-500" />,
  medication: <Pill className="h-4 w-4 text-purple-500" />,
  preparation: <ClipboardList className="h-4 w-4 text-amber-500" />,
  logistics: <MapPin className="h-4 w-4 text-green-500" />,
};

export function VisitPreparationCard() {
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());
  const grouped = getGroupedChecklist();

  const toggleItem = (itemId: string) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  const totalItems = genericPreparationItems.length;
  const checkedCount = checkedItems.size;
  const progress = totalItems > 0 ? Math.round((checkedCount / totalItems) * 100) : 0;

  return (
    <Card className="border border-gray-200">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-blue-500" />
          <CardTitle className="text-lg">Visit Preparation</CardTitle>
        </div>
        <p className="text-sm text-gray-500">{preparationHeaderMessage}</p>

        {/* Progress bar */}
        {checkedCount > 0 && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span>{checkedCount} of {totalItems} done</span>
              <span>{progress}%</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-gray-100">
              <div
                className="h-1.5 rounded-full bg-blue-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {grouped.map((group) => (
          <div key={group.category}>
            <div className="flex items-center gap-1.5 mb-2">
              {categoryIcons[group.category]}
              <h4 className="text-sm font-medium text-gray-700">
                {getCategoryLabel(group.category)}
              </h4>
            </div>
            <div className="space-y-2 pl-1">
              {group.items.map((item) => (
                <div key={item.id} className="flex items-start gap-2">
                  <Checkbox
                    id={item.id}
                    checked={checkedItems.has(item.id)}
                    onCheckedChange={() => toggleItem(item.id)}
                    className="mt-0.5"
                  />
                  <div className="flex-1">
                    <Label
                      htmlFor={item.id}
                      className={`text-sm cursor-pointer ${
                        checkedItems.has(item.id)
                          ? 'text-gray-400 line-through'
                          : 'text-gray-700'
                      }`}
                    >
                      {item.label}
                    </Label>
                    {item.description && (
                      <p
                        className={`text-xs mt-0.5 ${
                          checkedItems.has(item.id)
                            ? 'text-gray-300'
                            : 'text-gray-500'
                        }`}
                      >
                        {item.description}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        <p className="text-xs text-gray-400 italic pt-2 border-t border-gray-100">
          {preparationFooterMessage}
        </p>
      </CardContent>
    </Card>
  );
}
