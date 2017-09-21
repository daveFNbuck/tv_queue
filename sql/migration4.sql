CREATE TABLE `seen` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) unsigned NOT NULL,
  `episode_id` bigint(20) unsigned NOT NULL,
  `watch_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `episode_id` (`episode_id`),
  CONSTRAINT `seen_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `seen_ibfk_2` FOREIGN KEY (`episode_id`) REFERENCES `episode` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT INTO seen (user_id, episode_id, watch_time)
SELECT subscription.user_id, episode.id, null
FROM
    subscription
    JOIN episode USING(series_id)
    LEFT JOIN unseen ON
        subscription_id = subscription.id
        AND episode_id = episode.id
WHERE unseen.episode_id IS NULL;

DROP TABLE unseen;
