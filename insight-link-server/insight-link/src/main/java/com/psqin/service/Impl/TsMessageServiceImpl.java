package com.psqin.service.Impl;

import com.psqin.constant.MessageConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.TsMessageDTO;
import com.psqin.domain.entity.TeacherStudentMessage;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.mapper.TsGuidanceMapper;
import com.psqin.mapper.TsMessageMapper;
import com.psqin.result.PageResult;
import com.psqin.service.TsMessageService;
import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

import com.psqin.websocket.WebSocketServer;
import com.alibaba.fastjson.JSON;
import java.util.HashMap;
import java.util.Map;
import java.time.LocalDateTime;

/**
 *
 */
@Service
public class TsMessageServiceImpl implements TsMessageService {

    @Autowired
    private TsMessageMapper tsMessageMapper;

    @Autowired
    private TsGuidanceMapper tsGuidanceMapper;

    @Autowired
    private WebSocketServer webSocketServer;

    @Override
    public void save(TsMessageDTO tsMessageDTO) {
        if (tsMessageDTO == null || tsMessageDTO.getReceiverId() == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }

        Integer roleId = BaseContext.getRoleId();
        Long senderId = BaseContext.getCurrentId();
        Long receiverId = tsMessageDTO.getReceiverId();

        if (roleId == null || senderId == null) {
            throw new AccountNotAllowException(MessageConstant.USER_NOT_LOGIN);
        }

        if (Integer.valueOf(3).equals(roleId)) {
            Long bindTeacherId = tsGuidanceMapper.getTeacherUserIdByStudentUserId(senderId);
            if (bindTeacherId == null || !bindTeacherId.equals(receiverId)) {
                throw new AccountNotAllowException("未绑定该导师，无法发送留言");
            }
        } else if (Integer.valueOf(2).equals(roleId)) {
            Integer count = tsGuidanceMapper.countByTeacherAndStudent(senderId, receiverId);
            if (count == null || count == 0) {
                throw new AccountNotAllowException("未绑定该学生，无法发送留言");
            }
        } else {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }

        TeacherStudentMessage teacherStudentMessage = new TeacherStudentMessage();
        BeanUtils.copyProperties(tsMessageDTO, teacherStudentMessage);
        teacherStudentMessage.setSenderId(senderId);
        tsMessageMapper.insert(teacherStudentMessage);

        // 通过 WebSocket 推送消息给接收者
        Map<String, Object> wsMessage = new HashMap<>();
        wsMessage.put("type", "chat_message");
        wsMessage.put("senderId", senderId);
        wsMessage.put("content", tsMessageDTO.getContent());
        // 这里可以从查询或上下文中获取发送者的基本信息，简单起见传必要字段
        webSocketServer.sendToClient(String.valueOf(receiverId), JSON.toJSONString(wsMessage));
    }

    @Override
    public List<com.psqin.domain.vo.UserVO> listContacts() {
        Long userId = BaseContext.getCurrentId();
        if (userId == null) {
            throw new AccountNotAllowException(MessageConstant.USER_NOT_LOGIN);
        }
        return tsMessageMapper.listContacts(userId);
    }

    @Override
    public PageResult pageHistory(Long otherUserId, Integer page, Integer pageSize) {
        Long userId = BaseContext.getCurrentId();
        if (userId == null) {
            throw new AccountNotAllowException(MessageConstant.USER_NOT_LOGIN);
        }
        if (otherUserId == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        Integer cnt = tsMessageMapper.countConversation(userId, otherUserId);
        int p = page == null ? 1 : page;
        int ps = pageSize == null ? 20 : pageSize;
        PageHelper.startPage(p, ps);
        Page<com.psqin.domain.entity.TeacherStudentMessage> data = tsMessageMapper.pageHistory(userId, otherUserId);
        return new PageResult(data.getTotal(), data.getResult());
    }
}
