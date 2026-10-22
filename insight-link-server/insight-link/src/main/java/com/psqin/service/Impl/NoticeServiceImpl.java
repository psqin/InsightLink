package com.psqin.service.Impl;

import com.psqin.constant.MessageConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.NoticeDTO;
import com.psqin.domain.entity.SystemNotice;
import com.psqin.domain.vo.SystemNoticeVO;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.mapper.NoticeMapper;
import com.psqin.service.NoticeService;
import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.result.PageResult;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 *
 */
@Service
public class NoticeServiceImpl implements NoticeService {

    @Autowired private NoticeMapper noticeMapper;

    @Override
    @Transactional
    public void save(NoticeDTO noticeDTO) {
        Integer roleId = BaseContext.getRoleId();
        Long userId = BaseContext.getCurrentId();
        if (roleId == null || roleId == 3) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }

        SystemNotice systemNotice = new SystemNotice();
        BeanUtils.copyProperties(noticeDTO, systemNotice);
        systemNotice.setPublisherId(userId);
        systemNotice.setType(roleId);

        noticeMapper.insert(systemNotice);


    }

    @Override
    @Transactional
    public void delete(Long id) {
        Integer roleId = BaseContext.getRoleId();
        Long userId = BaseContext.getCurrentId();
        if (roleId == null || roleId == 3) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        SystemNotice existing = noticeMapper.getById(id);
        if (existing == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        if (!userId.equals(existing.getPublisherId())) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        noticeMapper.deleteById(id);
    }

    @Override
    @Transactional
    public void update(Long id, NoticeDTO noticeDTO) {
        Integer roleId = BaseContext.getRoleId();
        Long userId = BaseContext.getCurrentId();
        if (roleId == null || roleId == 3) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        SystemNotice existing = noticeMapper.getById(id);
        if (existing == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        if (!userId.equals(existing.getPublisherId())) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        SystemNotice update = new SystemNotice();
        update.setId(id);
        update.setTitle(noticeDTO.getTitle());
        update.setContent(noticeDTO.getContent());
        noticeMapper.update(update);
    }

    @Override
    public SystemNotice getById(Long id) {
        return noticeMapper.getById(id);
    }

    @Override
    public java.util.List<SystemNotice> listMy() {
        Long userId = BaseContext.getCurrentId();
        return noticeMapper.listByPublisherId(userId);
    }

    @Override
    public PageResult pageQueryMine(String title, java.time.LocalDateTime beginTime, java.time.LocalDateTime endTime, Integer page, Integer pageSize) {
        Long userId = BaseContext.getCurrentId();
        PageHelper.startPage(page, pageSize);
        Page<SystemNotice> p = noticeMapper.pageQueryMine(userId, title, beginTime, endTime);
        return new PageResult(p.getTotal(), p.getResult());
    }

    @Override
    public PageResult pageQueryAdmin(String publisherRealName, java.time.LocalDateTime beginTime, java.time.LocalDateTime endTime, Integer page, Integer pageSize) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        PageHelper.startPage(page, pageSize);
        Page<SystemNoticeVO> p = noticeMapper.pageQueryAdmin(publisherRealName, beginTime, endTime);
        return new PageResult(p.getTotal(), p.getResult());
    }

    @Override
    @Transactional
    public void deleteByAdmin(Long id) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        SystemNotice existing = noticeMapper.getById(id);
        if (existing == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        noticeMapper.deleteById(id);
    }

    @Override
    public SystemNoticeVO getDetailByAdmin(Long id) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        SystemNoticeVO vo = noticeMapper.getVOById(id);
        if (vo == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        return vo;
    }

    @Override
    @Transactional
    public void updateByAdmin(Long id, NoticeDTO noticeDTO) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        SystemNotice existing = noticeMapper.getById(id);
        if (existing == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        SystemNotice update = new SystemNotice();
        update.setId(id);
        update.setTitle(noticeDTO.getTitle());
        update.setContent(noticeDTO.getContent());
        noticeMapper.update(update);
    }
}
