ALTER TABLE `unseen` DROP FOREIGN KEY `unseen_ibfk_2`;
ALTER TABLE `episode` MODIFY COLUMN `id` BIGINT unsigned AUTO_INCREMENT;
ALTER TABLE `unseen` ADD CONSTRAINT `unseen_ibfk_2` FOREIGN KEY (`episode_id`) REFERENCES `episode`(`id`);
