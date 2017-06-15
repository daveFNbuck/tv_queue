ALTER TABLE `unseen` DROP FOREIGN KEY `unseen_ibfk_2`;
ALTER TABLE `unseen` ADD CONSTRAINT `unseen_ibfk_2` FOREIGN KEY (`episode_id`) REFERENCES `episode`(`id`) ON DELETE CASCADE ON UPDATE CASCADE;
