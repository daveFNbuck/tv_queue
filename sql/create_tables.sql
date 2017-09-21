USE tvq;

CREATE TABLE `user` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(20) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

CREATE TABLE `series` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL DEFAULT '',
  `air_time` time DEFAULT NULL,
  `episode_length` int(11) DEFAULT NULL,
  `last_updated` bigint(20) NOT NULL,
  `network` varchar(20) DEFAULT NULL,
  `banner` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

CREATE TABLE `episode` (
  `id` bigint(20) unsigned NOT NULL,
  `series_id` bigint(20) unsigned NOT NULL,
  `season` int(11) NOT NULL,
  `episode` int(11) NOT NULL,
  `title` varchar(50) DEFAULT '',
  `air_date` date DEFAULT NULL,
  `overview` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `show_season_episode` (`series_id`,`season`,`episode`),
  KEY `fk_show_id` (`series_id`),
  CONSTRAINT `episode_ibfk_1` FOREIGN KEY (`series_id`) REFERENCES `series` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `subscription` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) unsigned NOT NULL,
  `series_id` bigint(20) unsigned NOT NULL,
  `shift_len` int(11) NOT NULL DEFAULT '0',
  `shift_type` enum('HOURS','DAYS') NOT NULL DEFAULT 'HOURS',
  `enabled` tinyint(4) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `subscription` (`user_id`,`series_id`),
  KEY `series_id` (`series_id`),
  CONSTRAINT `subscription_ibfk_2` FOREIGN KEY (`series_id`) REFERENCES `series` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `subscription_ibfk_3` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=94 DEFAULT CHARSET=utf8;

CREATE TABLE `seen` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) unsigned NOT NULL,
  `episode_id` bigint(20) unsigned NOT NULL,
  `watch_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `episode_id` (`episode_id`),
  CONSTRAINT `seen_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `seen_ibfk_2` FOREIGN KEY (`episode_id`) REFERENCES `episode` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
