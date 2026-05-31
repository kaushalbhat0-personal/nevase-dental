import { motion, AnimatePresence } from 'framer-motion';
import { contentFadeVariants } from './variants';

interface FadeContentProps {
  show: boolean;
  children: React.ReactNode;
  className?: string;
}

export function FadeContent({ show, children, className = '' }: FadeContentProps) {
  return (
    <AnimatePresence mode="wait">
      {show && (
        <motion.div
          key="content"
          initial="hidden"
          animate="visible"
          exit="hidden"
          variants={contentFadeVariants}
          className={className}
          style={{ willChange: 'opacity' }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
