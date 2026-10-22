package com.psqin.mapper;

import com.psqin.domain.entity.SystemNotice;
import com.psqin.domain.vo.SystemNoticeVO;
import com.github.pagehelper.Page;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 *
 */
@Mapper
public interface NoticeMapper {


    void insert(SystemNotice systemNotice);

    void deleteById(@Param("id") Long id);

    void update(SystemNotice systemNotice);

    SystemNotice getById(@Param("id") Long id);

    java.util.List<SystemNotice> listByPublisherId(@Param("publisherId") Long publisherId);

    Page<SystemNotice> pageQueryMine(@Param("publisherId") Long publisherId,
                                     @Param("title") String title,
                                     @Param("beginTime") java.time.LocalDateTime beginTime,
                                     @Param("endTime") java.time.LocalDateTime endTime);

    Page<SystemNoticeVO> pageQueryAdmin(@Param("publisherRealName") String publisherRealName,
                                        @Param("beginTime") java.time.LocalDateTime beginTime,
                                        @Param("endTime") java.time.LocalDateTime endTime);

    SystemNoticeVO getVOById(@Param("id") Long id);

    java.util.List<SystemNoticeVO> listLatestByTypeAndPublisher(@Param("type") Integer type,
                                                                @Param("publisherId") Long publisherId,
                                                                @Param("limit") Integer limit);

    @org.apache.ibatis.annotations.Select("select count(*) from system_notice where type = #{type}")
    Integer countByType(@Param("type") Integer type);

    @org.apache.ibatis.annotations.Select("select date(publish_time) as day, count(*) as count from system_notice where type = #{type} and publish_time >= #{startTime} group by date(publish_time) order by day")
    java.util.List<com.psqin.domain.vo.DailyCountVO> listDailyCountByType(@Param("type") Integer type, @Param("startTime") java.time.LocalDateTime startTime);

    @org.apache.ibatis.annotations.Select("select count(*) from system_notice where type = #{type} and publisher_id = #{publisherId}")
    Integer countByTypeAndPublisher(@Param("type") Integer type, @Param("publisherId") Long publisherId);
}
