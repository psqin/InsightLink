package com.psqin.service;

import com.psqin.domain.dto.NoticeDTO;
import com.psqin.domain.entity.SystemNotice;
import com.psqin.domain.vo.SystemNoticeVO;
import com.psqin.result.PageResult;
import java.util.List;

public interface NoticeService {
    void save(NoticeDTO noticeDTO);

    void delete(Long id);

    void update(Long id, NoticeDTO noticeDTO);

    SystemNotice getById(Long id);

    List<SystemNotice> listMy();

    PageResult pageQueryMine(String title, java.time.LocalDateTime beginTime, java.time.LocalDateTime endTime, Integer page, Integer pageSize);

    PageResult pageQueryAdmin(String publisherRealName, java.time.LocalDateTime beginTime, java.time.LocalDateTime endTime, Integer page, Integer pageSize);

    void deleteByAdmin(Long id);

    SystemNoticeVO getDetailByAdmin(Long id);

    void updateByAdmin(Long id, NoticeDTO noticeDTO);
}
