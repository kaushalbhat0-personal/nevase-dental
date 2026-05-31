import { useState, useEffect } from 'react';
import type { HealthNewsItem } from '../../types';

const mockNews: HealthNewsItem[] = [
  {
    id: 1,
    title: 'New Breakthrough in Heart Disease Treatment',
    description: 'Researchers have discovered a promising new approach to treating cardiovascular disease with minimal side effects.',
    category: 'Research',
    published_at: new Date().toISOString(),
  },
  {
    id: 2,
    title: 'Flu Season Updates: What You Need to Know',
    description: 'CDC releases latest guidelines for flu prevention and vaccination recommendations for this season.',
    category: 'Public Health',
    published_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: 3,
    title: 'Mental Health Awareness Month',
    description: 'Join us in recognizing the importance of mental health care and resources available for patients.',
    category: 'Awareness',
    published_at: new Date(Date.now() - 172800000).toISOString(),
  },
  {
    id: 4,
    title: 'AI in Healthcare: Transforming Patient Care',
    description: 'How artificial intelligence is revolutionizing diagnostics and improving patient outcomes.',
    category: 'Technology',
    published_at: new Date(Date.now() - 259200000).toISOString(),
  },
];

export function HealthNews() {
  const [news, setNews] = useState<HealthNewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setNews(mockNews);
      setLoading(false);
    }, 500);
  }, []);

  if (loading) {
    return (
      <div className="health-news">
        <h3 className="panel-title">📰 Health News</h3>
        <div className="news-loading">
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
          <div className="skeleton-line" />
        </div>
      </div>
    );
  }

  return (
    <div className="health-news">
      <h3 className="panel-title">📰 Health News</h3>
      <div className="news-list">
        {news.map((item) => (
          <article key={item.id} className="news-item">
            <span className="news-category">{item.category}</span>
            <h4 className="news-title">{item.title}</h4>
            <p className="news-description">{item.description}</p>
            <time className="news-date">
              {new Date(item.published_at).toLocaleDateString()}
            </time>
          </article>
        ))}
      </div>
    </div>
  );
}
